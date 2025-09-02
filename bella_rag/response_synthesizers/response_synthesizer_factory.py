from typing import Callable, Optional, List

from llama_index.core import get_response_synthesizer
from llama_index.core.bridge.pydantic import BaseModel
from llama_index.core.callbacks.base import CallbackManager
from llama_index.core.indices.prompt_helper import PromptHelper
from llama_index.core.prompts import BasePromptTemplate
from llama_index.core.response_synthesizers.base import BaseSynthesizer
from llama_index.core.response_synthesizers.type import ResponseMode
from llama_index.core.service_context import ServiceContext
from llama_index.core.service_context_elements.llm_predictor import LLMPredictorType
from llama_index.core.types import BasePydanticProgram
from openai._types import Headers

from bella_rag.preprocessor.ProcessorGenerators import CustomGenerator
from bella_rag.prompts.prompts import PromptTemplate
from bella_rag.response_synthesizers.simple_llm_summarize import SimpleLLMSummarize


def get_llm_response_synthesizer(
        llm: Optional[LLMPredictorType] = None,
        model: Optional[str] = None,
        instruction: Optional[str] = None,
        max_tokens: Optional[int] = None,
        prompt_helper: Optional[PromptHelper] = None,
        service_context: Optional[ServiceContext] = None,
        text_qa_template: Optional[BasePromptTemplate] = None,
        refine_template: Optional[BasePromptTemplate] = None,
        summary_template: Optional[BasePromptTemplate] = None,
        simple_template: Optional[BasePromptTemplate] = None,
        response_mode: ResponseMode = ResponseMode.COMPACT,
        callback_manager: Optional[CallbackManager] = None,
        use_async: bool = False,
        streaming: bool = False,
        structured_answer_filtering: bool = False,
        output_cls: Optional[BaseModel] = None,
        program_factory: Optional[Callable[[PromptTemplate], BasePydanticProgram]] = None,
        response_generators: Optional[List[CustomGenerator]] = None,
        verbose: bool = False,
        extra_headers: Optional[Headers] = None,
) -> BaseSynthesizer:
    synthesizer = get_response_synthesizer(
        llm=llm,
        prompt_helper=prompt_helper,
        service_context=service_context,
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        summary_template=summary_template,
        simple_template=simple_template,
        response_mode=response_mode,
        callback_manager=callback_manager,
        use_async=use_async,
        streaming=streaming,
        structured_answer_filtering=structured_answer_filtering,
        output_cls=output_cls,
        program_factory=program_factory,
        verbose=verbose,
    )
    if response_mode == ResponseMode.SIMPLE_SUMMARIZE:
        return transform_simple_summarize(synthesizer, model, instruction, max_tokens,
                                          response_generators, extra_headers, output_cls)
    return synthesizer


def transform_simple_summarize(
        simple_summarize: Optional[BaseSynthesizer] = None,
        model: Optional[str] = None,
        instruction: Optional[str] = None,
        max_tokens: Optional[int] = None,
        response_generators: Optional[List[CustomGenerator]] = None,
        extra_headers: Optional[Headers] = None,
        output_cls: Optional[BaseModel] = None,
) -> SimpleLLMSummarize:
    return SimpleLLMSummarize(
        llm=simple_summarize._llm,
        callback_manager=simple_summarize._callback_manager,
        prompt_helper=simple_summarize._prompt_helper,
        text_qa_template=simple_summarize._text_qa_template,
        streaming=simple_summarize._streaming,
        model=model,
        instruction=instruction,
        max_tokens=max_tokens,
        response_generators=response_generators,
        extra_headers=extra_headers,
        output_cls=output_cls,
    )
