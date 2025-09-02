from typing import List

import numpy as np
from numpy.linalg import norm

from app.services import ak
from init.settings import VECTOR_DB_COMMON
from bella_rag.llm.openapi import OpenAPIEmbedding

embed_model = OpenAPIEmbedding(model=VECTOR_DB_COMMON["EMBEDDING_MODEL"],
                               embedding_batch_size=VECTOR_DB_COMMON["EMBEDDING_BATCH_SIZE"],
                               api_key=ak, model_dimension=int(VECTOR_DB_COMMON["DIMENSION"]))


def compute_texts_similarity(query: str, texts: List[str]) -> List[float]:
    similarities = []
    text_list = [query]
    text_list.extend(texts)
    embeddings = embed_model._get_text_embeddings(text_list)
    query_embedding = embeddings[0]
    # 计算余弦相似度
    for embedding in embeddings[1:]:
        similarities.append(compute_cosine_similarity(query_embedding, embedding))
    return similarities


def compute_cosine_similarity(query_embedding: List[float], embedding: List[float]) -> float:
    """
    余弦相似度计算
    """
    if not embedding:
        return 0
    return float(np.dot(query_embedding, embedding) / (norm(query_embedding) * norm(embedding)))
