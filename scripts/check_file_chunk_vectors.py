#!/usr/bin/env python3
"""Check whether the active vector store contains chunk vectors for a file."""

import argparse
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KE_BUSINESS_DIR = PROJECT_ROOT / "ke_business"


def setup_project() -> None:
    """Load project settings without starting Django workers or schedulers."""
    sys.path.insert(0, str(PROJECT_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "init.settings")

    import init
    import init.const

    # 配置文件路径与 ke_business/manage.py 保持一致，但不调用 django.setup()，
    # 从而避免一次只读检查意外启动 Kafka 消费者和定时任务。
    init.const.BASE_DIR = str(KE_BUSINESS_DIR).replace("\\", "/")
    init.const.SECRET_KEY = "temporary-vector-check-script"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="查询指定文件在当前配置的向量数据库中是否存在切片向量",
    )
    parser.add_argument("file_id", help="要查询的文件 ID")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    setup_project()

    from init.settings import QDRANT_VECTOR_DB, TENCENT_VECTOR_DB, VECTOR_DB_TYPE

    db_type = VECTOR_DB_TYPE.lower()
    if db_type == "qdrant":
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue

        client_kwargs = {
            "api_key": QDRANT_VECTOR_DB["API_KEY"] or None,
        }
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
        points, _ = client.scroll(
            collection_name=QDRANT_VECTOR_DB["COLLECTION_NAME"],
            scroll_filter=Filter(must=[
                FieldCondition(
                    key="source_id",
                    match=MatchValue(value=args.file_id),
                ),
            ]),
            limit=1,
            with_payload=True,
            with_vectors=True,
        )
        sample = points[0] if points else None
        embedding = sample.vector if sample is not None else None
        sample_node_id = (
            (sample.payload or {}).get("original_node_id", str(sample.id))
            if sample is not None
            else None
        )
    else:
        from tcvectordb import VectorDBClient
        from tcvectordb.model.enum import ReadConsistency
        from tcvectordb.model.document import Filter

        client = VectorDBClient(
            url=TENCENT_VECTOR_DB["URL"],
            username="root",
            key=TENCENT_VECTOR_DB["KEY"],
            read_consistency=ReadConsistency.STRONG_CONSISTENCY,
            timeout=30,
        )
        # 直接读取原始 Document，避免业务节点类型转换时丢弃 image 节点的
        # vector 字段，导致把“存在向量”误判为“只有元数据”。
        escaped_file_id = args.file_id.replace("\\", "\\\\").replace('"', '\\"')
        documents = client.query(
            database_name=TENCENT_VECTOR_DB["DATABASE_NAME"],
            collection_name=TENCENT_VECTOR_DB["COLLECTION_NAME"],
            filter=Filter(cond=f'source_id = "{escaped_file_id}"'),
            offset=0,
            limit=1,
            retrieve_vector=True,
        )
        sample = documents[0] if documents else None
        embedding = sample.get("vector") if sample is not None else None
        sample_node_id = sample.get("id") if sample is not None else None

    result = {
        "file_id": args.file_id,
        "vector_db_type": db_type,
        "exists": sample is not None,
        "sample_node_id": sample_node_id,
        "has_embedding": bool(embedding),
        "vector_dimension": len(embedding) if embedding else 0,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if sample is not None else 1


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
