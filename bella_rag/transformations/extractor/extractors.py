from abc import abstractmethod, ABC

from bella_openapi.bella_trace import TraceContext

from app.services import extract_service
from app.services.extract_service import extract_store_summary_question
from init.settings import OPENAPI
from bella_rag.llm.openapi import OpenAPI
from bella_rag.transformations.extractor.extract_context import context_summary
from bella_rag.transformations.extractor.extract_tag import extract_tag_impl

llm = OpenAPI(model="gpt-4o", temperature=0.01, api_base=OPENAPI["URL"], api_key=OPENAPI["AK"], timeout=300)
EXTRACTOR_CONTEXT = "context_extractor"
EXTRACTOR_SUMMARY = "summary_extractor"


class Extractor(ABC):
    @abstractmethod
    def extract(self, source_id, **kwargs):
        """
        用于从给定的文件中提取数据。
        :param source_id: 文件的唯一标识符
        """
        pass

    @abstractmethod
    def type(self) -> str:
        pass


class SummaryQuestionExtractor(Extractor):

    def extract(self, source_id, source_name: str = None, **kwargs):
        if source_name is None:
            return

        TraceContext.trace_id = source_id
        extract_store_summary_question(source_id, source_name, llm)

    def type(self) -> str:
        return EXTRACTOR_SUMMARY


class TagExtractor(Extractor):
    """
    暂时无场景使用该提取器
    """

    def extract(self, source_id, source_name: str = None, **kwargs):
        if source_name is None:
            return

        documents = extract_service.load_file_document(file_id=source_id, file_name=source_name)
        TraceContext.trace_id = source_id
        extract_tag_impl(source_id, documents)

    def type(self) -> str:
        return "tag_extractor"


class ContextExtractor(Extractor):

    def extract(self, source_id, **kwargs):
        context_summary(source_id)

    def type(self) -> str:
        return EXTRACTOR_CONTEXT
