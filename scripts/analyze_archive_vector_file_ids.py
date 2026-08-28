#!/usr/bin/env python3
"""对比向量库文件 ID 与待归档文件 ID，并输出集合交集。

示例：
    unset ENVTYPE
    .venv/bin/python scripts/analyze_archive_vector_file_ids.py \
        --base-url http://127.0.0.1:8008 \
        --output-dir /tmp/ke-rag-archive-analysis
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from list_vector_file_ids import (
    SOURCE_ID_FIELD,
    scan_qdrant,
    scan_tencent,
    setup_project,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="扫描向量库文件 ID、查询待归档文件 ID，并计算两者交集",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8008",
        help="ke-RAG 服务地址，默认 http://127.0.0.1:8008",
    )
    parser.add_argument(
        "--authorization",
        help="接口 Authorization；默认读取当前项目配置 OPENAPI.AK",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="向量库每页读取数量，默认 1000",
    )
    parser.add_argument(
        "--progress-pages",
        type=int,
        default=10,
        help="每扫描多少页输出一次进度，0 表示关闭，默认 10",
    )
    parser.add_argument(
        "--http-timeout",
        type=int,
        default=300,
        help="dry-run HTTP 请求超时秒数，默认 300",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp") / (
            "ke-rag-archive-analysis-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        ),
        help="结果目录，默认使用带时间戳的 /tmp 目录",
    )
    args = parser.parse_args()
    if args.page_size <= 0:
        parser.error("--page-size 必须大于 0")
    if args.progress_pages < 0:
        parser.error("--progress-pages 不能小于 0")
    if args.http_timeout <= 0:
        parser.error("--http-timeout 必须大于 0")
    return args


def write_json(path: Path, data: Dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_lines(path: Path, values: Iterable[str]) -> None:
    values = list(values)
    path.write_text(
        "\n".join(values) + ("\n" if values else ""),
        encoding="utf-8",
    )


def scan_vector_file_ids(
        db_type: str,
        page_size: int,
        progress_pages: int,
) -> Dict:
    if db_type == "qdrant":
        documents, expected_count, collection_name = scan_qdrant(page_size)
    else:
        documents, expected_count, collection_name = scan_tencent(page_size)

    chunk_counts = Counter()
    scanned_count = 0
    missing_source_id_count = 0
    for document in documents:
        scanned_count += 1
        file_id = document.get(SOURCE_ID_FIELD)
        if file_id:
            chunk_counts[str(file_id)] += 1
        else:
            missing_source_id_count += 1

        page, remainder = divmod(scanned_count, page_size)
        if (
                remainder == 0
                and progress_pages
                and page % progress_pages == 0
        ):
            print(
                f"已扫描 {scanned_count} 条切片向量，"
                f"发现 {len(chunk_counts)} 个文件 ID",
                file=sys.stderr,
                flush=True,
            )

    sorted_counts = dict(sorted(chunk_counts.items()))
    return {
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


def fetch_archive_dry_run(base_url: str, authorization: str, timeout: int) -> Dict:
    url = base_url.rstrip("/") + "/api/vector/archive"
    request = Request(
        url=url,
        data=json.dumps({"dry_run": True}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": authorization,
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"dry-run接口返回HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"无法访问dry-run接口: {error.reason}") from error

    file_ids = data.get("file_ids")
    if not isinstance(file_ids, list):
        raise RuntimeError(f"dry-run接口未返回file_ids数组: {data}")
    return data


def build_comparison(vector_result: Dict, dry_run_result: Dict) -> Dict:
    vector_ids = set(vector_result["file_ids"])
    dry_run_ids = set(dry_run_result["file_ids"])
    intersection = sorted(vector_ids & dry_run_ids)
    return {
        "vector_file_id_count": len(vector_ids),
        "dry_run_file_id_count": len(dry_run_ids),
        "intersection_file_id_count": len(intersection),
        "vector_only_file_id_count": len(vector_ids - dry_run_ids),
        "dry_run_only_file_id_count": len(dry_run_ids - vector_ids),
        "vector_scan": {
            "expected_vector_count_at_start": vector_result.get(
                "expected_vector_count_at_start"
            ),
            "scanned_vector_count": vector_result["scanned_vector_count"],
            "scan_count_matches_start_count": vector_result[
                "scan_count_matches_start_count"
            ],
            "missing_source_id_vector_count": vector_result[
                "missing_source_id_vector_count"
            ],
        },
        "intersection_file_ids": intersection,
        "vector_only_file_ids": sorted(vector_ids - dry_run_ids),
        "dry_run_only_file_ids": sorted(dry_run_ids - vector_ids),
    }


def main() -> int:
    args = parse_args()
    setup_project()

    from init.settings import OPENAPI, VECTOR_DB_TYPE

    authorization = args.authorization or OPENAPI["AK"]
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("1/3 扫描向量数据库文件 ID", file=sys.stderr)
    vector_result = scan_vector_file_ids(
        VECTOR_DB_TYPE.lower(),
        args.page_size,
        args.progress_pages,
    )
    write_json(output_dir / "vector_file_ids.json", vector_result)

    print("2/3 调用归档 dry-run 接口", file=sys.stderr)
    dry_run_result = fetch_archive_dry_run(
        args.base_url,
        authorization,
        args.http_timeout,
    )
    write_json(output_dir / "archive_dry_run.json", dry_run_result)

    print("3/3 计算文件 ID 交集", file=sys.stderr)
    comparison = build_comparison(vector_result, dry_run_result)
    write_json(output_dir / "comparison.json", comparison)
    write_lines(
        output_dir / "intersection_file_ids.txt",
        comparison["intersection_file_ids"],
    )
    write_lines(
        output_dir / "vector_only_file_ids.txt",
        comparison["vector_only_file_ids"],
    )
    write_lines(
        output_dir / "dry_run_only_file_ids.txt",
        comparison["dry_run_only_file_ids"],
    )

    summary = {
        key: value
        for key, value in comparison.items()
        if not key.endswith("_file_ids")
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"完整结果目录: {output_dir}", file=sys.stderr)

    if not vector_result["scan_count_matches_start_count"]:
        print(
            "警告：向量扫描数量与扫描开始时不一致，建议在低峰期重新执行。",
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
