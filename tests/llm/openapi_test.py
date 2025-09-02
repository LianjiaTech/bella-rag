from app.common.contexts import UserContext
from app.services import ak
from init.config import conf_dict
from init.settings import VECTOR_DB_COMMON
from bella_rag.llm.openapi import OpenAPIEmbedding, OpenAPI, Rerank
from bella_rag.utils.embedding_util import compute_texts_similarity
from bella_rag.utils.user_util import get_user_info


def test_embedding():
    UserContext.user_id = get_user_info()
    dimension = int(VECTOR_DB_COMMON["DIMENSION"])
    embed_model = OpenAPIEmbedding(model=VECTOR_DB_COMMON["EMBEDDING_MODEL"],
                                   embedding_batch_size=VECTOR_DB_COMMON["EMBEDDING_BATCH_SIZE"],
                                   api_key=ak, model_dimension=dimension)
    text = "我是中国人"
    embed = embed_model.get_text_embedding(text)
    # 数组大小dimension
    assert len(embed) == dimension


def test_completion():
    UserContext.user_id = get_user_info()
    llm = OpenAPI(model="gpt-4o", temperature=0.01, max_tokens=4000, api_base=OpenAPI['URL'],
                  api_key=OpenAPI['AK'])
    text = "我是中国人"
    completion = llm.complete(text)
    assert completion is not None


def test_rerank():
    rerank = Rerank(conf_dict["RERANK"]["api_base"], conf_dict["RERANK"]["model"])
    res = rerank.rerank("我是中国人", ["我是中国人", "我是美国人", "我是日本人"])
    assert res is not None
    print(res)


def test_similarity_compute():
    res = compute_texts_similarity("我是中国人", ["我是中国人", "我是美国人", "我是日本人"])
    assert res is not None
    print(res)
