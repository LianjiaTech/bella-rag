import io

from llama_index.core import DocumentSummaryIndex, get_response_synthesizer
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.response_synthesizers import ResponseMode

from app.common.contexts import UserContext
from app.services import embed_model
from init.settings import OPENAPI
from bella_rag.llm.openapi import OpenAPI
from bella_rag.transformations.factory import TransformationFactory
from tests import TEST_PATH


def test_summary():
    UserContext.user_id = "mock_user_id"
    file_path = TEST_PATH + "/resources/测试.pdf"

    with open(file_path, 'rb') as file:
        file_bytes = file.read()
        reader = TransformationFactory.get_reader('pdf')
        documents = reader.load_data(io.BytesIO(file_bytes))
        assert len(documents) > 0

    llm = OpenAPI(model="gpt-4o", temperature=0.01,
                  api_base=OPENAPI["URL"],
                  api_key=OPENAPI["AK"])
    response_synthesizer = get_response_synthesizer(response_mode=ResponseMode.TREE_SUMMARIZE, llm=llm,
                                                    streaming=False)
    splitter = SentenceSplitter(chunk_size=256, chunk_overlap=64)

    # 框架问题：
    # 1、stream为True，会有问题，会进行强转，转换为非流式的stream，取response属性，会报错，这块框架问题需要兼容
    # 2、embed_model不需要也要传入，就算embed_summaries为False不使用向量化都不可以
    # 3、传入的SentenceSplitter切分器（不传也会拿个默认的切分），将文件切分成多块，然后再用换行符拼接起来。
    #    最后使用get_response_synthesizer方法传入的prompt_helper（没传入有默认的，使用llm元数据进行），进行组合，进行递归的总结，最后输出一个结果
    doc_summary_index = DocumentSummaryIndex.from_documents(llm=llm, stream=False, embed_summaries=False,
                                                            embed_model=embed_model,
                                                            # transformations=[splitter],
                                                            documents=documents,
                                                            response_synthesizer=response_synthesizer
                                                            )
    print(doc_summary_index)

