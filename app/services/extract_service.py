from llama_index.core.schema import TextNode

from app.models.knowledge_file_meta_model import KnowledgeFileMeta
from app.services import embed_model
from app.services.knowledge_file_meta_service import KnowledgeMetaService
from common.tool.vector_db_tool import summary_question_vector_store
from init.settings import user_logger
from bella_rag.llm.openapi import OpenAPI
from bella_rag.transformations.extractor import extract_summary_question
from bella_rag.transformations.factory import TransformationFactory
from bella_rag.transformations.reader.pdf_reader import PdfReader
from bella_rag.utils.file_api_tool import file_api_client
from bella_rag.utils.file_util import get_file_type
from bella_rag.utils.trace_log_util import trace
from bella_rag.utils.user_util import get_user_info


@trace(step='summary_question', progress='summary_question')
def extract_store_summary_question(file_id: str, file_name: str, llm: OpenAPI):
    documents = load_file_document(file_id=file_id, file_name=file_name)
    if not documents:
        return

    summary_question = extract_summary_question.run(documents=documents, user=get_user_info(),
                                                    llm=llm, embed_model=embed_model)
    # DB存储
    data = KnowledgeFileMeta(summary_question=summary_question, file_id=file_id)
    KnowledgeMetaService.save(data)
    # 向量库存储
    embedding = embed_model.get_text_embedding(text=summary_question)
    summary_question_node = TextNode(text=summary_question, embedding=embedding, embed_model=embed_model)
    summary_question_node.id_ = file_id
    summary_question_node.metadata['source_id'] = file_id
    summary_question_vector_store.add(nodes=[summary_question_node])


def load_file_document(file_id: str, file_name: str):
    file_type = get_file_type(file_name)
    if file_type == 'docx' or file_type == 'doc':
        doc2pdf_file_id = file_api_client.get_docx_file_pdf_id(file_id)
        if not doc2pdf_file_id:
            user_logger.warn(f"doc文件找不到转换的pdf文件id file_id = {file_id} file_name = {file_name}")
            return
        reader = PdfReader()
        return reader.load_file(file_id=doc2pdf_file_id)
    else:
        reader = TransformationFactory.get_reader(file_type)
        if not reader:
            user_logger.info(f"不支持的文件类型 file_id = {file_id} file_name = {file_name}")
            return None
        return reader.load_file(file_id=file_id)
