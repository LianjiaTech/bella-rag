#!/usr/bin/env python3
"""分页扫描当前切片向量集合，统计其中全部文件 ID。"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterator, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KE_BUSINESS_DIR = PROJECT_ROOT / "ke_business"
SOURCE_ID_FIELD = "source_id"


def setup_project() -> None:
    """加载与本地 Django 服务相同的配置，但不启动 Django worker。"""
    sys.path.insert(0, str(PROJECT_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "init.settings")

    import init.const

    init.const.BASE_DIR = str(KE_BUSINESS_DIR).replace("\\", "/")
    init.const.SECRET_KEY = "temporary-vector-file-id-scan"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="统计当前切片向量集合中的全部 source_id 及其切片数量",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="每页读取的向量记录数，默认 1000",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="将 JSON 结果写入指定文件；不传时输出到 stdout",
    )
    parser.add_argument(
        "--progress-pages",
        type=int,
        default=10,
        help="每扫描多少页向 stderr 输出一次进度，0 表示不输出，默认 10",
    )
    args = parser.parse_args()
    if args.page_size <= 0:
        parser.error("--page-size 必须大于 0")
    if args.progress_pages < 0:
        parser.error("--progress-pages 不能小于 0")
    return args


def report_progress(page: int, scanned: int, unique_files: int, interval: int) -> None:
    if interval and page % interval == 0:
        print(
            f"已扫描 {scanned} 条切片向量，发现 {unique_files} 个文件 ID",
            file=sys.stderr,
            flush=True,
        )


def scan_tencent(page_size: int) -> tuple[Iterator[Dict], Optional[int], str]:
    from init.settings import TENCENT_VECTOR_DB
    from tcvectordb import VectorDBClient
    from tcvectordb.model.enum import ReadConsistency

    client = VectorDBClient(
        url=TENCENT_VECTOR_DB["URL"],
        username="root",
        key=TENCENT_VECTOR_DB["KEY"],
        read_consistency=ReadConsistency.STRONG_CONSISTENCY,
        timeout=30,
    )
    database_name = TENCENT_VECTOR_DB["DATABASE_NAME"]
    collection_name = TENCENT_VECTOR_DB["COLLECTION_NAME"]
    expected_count = client.count(
        database_name=database_name,
        collection_name=collection_name,
        timeout=30,
    )

    def documents() -> Iterator[Dict]:
        offset = 0
        while True:
            rows = client.query(
                database_name=database_name,
                collection_name=collection_name,
                offset=offset,
                limit=page_size,
                retrieve_vector=False,
                output_fields=[SOURCE_ID_FIELD],
                timeout=30,
            )
            if not rows:
                break
            yield from rows
            offset += len(rows)
            if len(rows) < page_size:
                break

    return documents(), expected_count, collection_name


def scan_qdrant(page_size: int) -> tuple[Iterator[Dict], Optional[int], str]:
    from init.settings import QDRANT_VECTOR_DB
    from qdrant_client import QdrantClient

    client_kwargs = {"api_key": QDRANT_VECTOR_DB["API_KEY"] or None}
    if QDRANT_VECTOR_DB["URL"]:
        client_kwargs["url"] = QDRANT_VECTOR_DB["URL"]
    else:
        client_kwargs.update({
            "host": QDRANT_VECTOR_DB["HOST"],
            "port": QDRANT_VECTOR_DB["PORT"],
            "grpc_port": QDRANT_VECTOR_DB["GRPC_PORT"],
            "prefer_grpc": QDRANT_VECTOR_DB["PREFER_GRPC"],
        })
    client = QdrantClient(**client_kwargs)
    collection_name = QDRANT_VECTOR_DB["COLLECTION_NAME"]
    expected_count = client.count(
        collection_name=collection_name,
        exact=True,
    ).count

    def documents() -> Iterator[Dict]:
        offset = None
        while True:
            points, next_offset = client.scroll(
                collection_name=collection_name,
                offset=offset,
                limit=page_size,
                with_payload=[SOURCE_ID_FIELD],
                with_vectors=False,
            )
            for point in points:
                yield point.payload or {}
            if next_offset is None:
                break
            offset = next_offset

    return documents(), expected_count, collection_name


def write_result(result: Dict, output: Optional[Path]) -> None:
    content = json.dumps(result, ensure_ascii=False, indent=2)
    if output is None:
        print(content)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content + "\n", encoding="utf-8")
    print(f"统计结果已写入: {output.resolve()}", file=sys.stderr)


def main() -> int:
    args = parse_args()
    setup_project()

    from init.settings import VECTOR_DB_TYPE

    db_type = VECTOR_DB_TYPE.lower()
    if db_type == "qdrant":
        documents, expected_count, collection_name = scan_qdrant(args.page_size)
    else:
        documents, expected_count, collection_name = scan_tencent(args.page_size)

    chunk_counts = Counter()
    missing_source_id_count = 0
    scanned_count = 0
    page = 0
    for document in documents:
        scanned_count += 1
        file_id = document.get(SOURCE_ID_FIELD)
        if file_id:
            chunk_counts[str(file_id)] += 1
        else:
            missing_source_id_count += 1
        if scanned_count % args.page_size == 0:
            page += 1
            report_progress(
                page,
                scanned_count,
                len(chunk_counts),
                args.progress_pages,
            )

    sorted_counts = dict(sorted(chunk_counts.items()))
    result = {
        "vector_db_type": db_type,
        "collection_name": collection_name,
        "expected_vector_count_at_start": expected_count,
        "scanned_vector_count": scanned_count,
        "file_id_count": len(sorted_counts),
        "missing_source_id_vector_count": missing_source_id_count,
        "scan_count_matches_start_count": (
            expected_count is None or scanned_count == expected_count
        ),
        "file_ids": list(sorted_counts),
        "chunk_count_by_file_id": sorted_counts,
    }
    write_result(result, args.output)

    if expected_count is not None and scanned_count != expected_count:
        print(
            "警告：扫描数量与开始时的集合数量不一致；扫描期间可能发生了上传、删除，"
            "或向量库分页结果不稳定，建议在低峰期重试。",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(
            json.dumps(
                {"error": str(error), "type": type(error).__name__},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
