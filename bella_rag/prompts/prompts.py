from typing import Optional, Dict, Any, Callable

from llama_index.core import PromptTemplate as LlamaPromptTemplate
from llama_index.core.prompts import PromptType
from llama_index.core.types import BaseOutputParser
from llama_index.legacy.llms.base import BaseLLM


class SafeFormatter(dict):
    def __missing__(self, key):
        return '{' + key + '}'


class PromptTemplate(LlamaPromptTemplate):
    template: str

    def __init__(
            self,
            template: str,
            prompt_type: str = PromptType.CUSTOM,
            output_parser: Optional[BaseOutputParser] = None,
            metadata: Optional[Dict[str, Any]] = None,
            template_var_mappings: Optional[Dict[str, Any]] = None,
            function_mappings: Optional[Dict[str, Callable]] = None,
            **kwargs: Any,
    ) -> None:
        super().__init__(
            template=template,
            prompt_type=prompt_type,
            metadata=metadata,
            output_parser=output_parser,
            template_var_mappings=template_var_mappings,
            function_mappings=function_mappings,
            **kwargs,
        )

    def format(
            self,
            llm: Optional[BaseLLM] = None,
            completion_to_prompt: Optional[Callable[[str], str]] = None,
            **kwargs: Any,
    ) -> str:
        """Format the prompt into a string."""
        del llm  # unused
        all_kwargs = {
            **self.kwargs,
            **kwargs,
        }

        mapped_all_kwargs = self._map_all_vars(all_kwargs)
        prompt = self.template.format_map(SafeFormatter(**mapped_all_kwargs))

        if self.output_parser is not None:
            prompt = self.output_parser.format(prompt)

        if completion_to_prompt is not None:
            prompt = completion_to_prompt(prompt)

        return prompt
