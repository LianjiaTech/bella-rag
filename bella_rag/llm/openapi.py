import json
import random
import time
import traceback
from io import BytesIO
from typing import Any, Optional, List, Dict, Sequence, cast, Generator, Union, BinaryIO, Tuple

import requests
from bella_openapi import StandardDomTree
from bella_openapi.bella_trace import TRACE_ID
from llama_index.core import BasePromptTemplate
from llama_index.core.base.embeddings.base import BaseEmbedding, Embedding
from llama_index.core.base.llms.types import LLMMetadata, CompletionResponseGen
from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.core.instrumentation.events.llm import LLMPredictStartEvent, LLMPredictEndEvent
from llama_index.core.llms.callbacks import llm_chat_callback
from llama_index.core.llms.llm import dispatcher
from llama_index.embeddings.openai.base import get_embeddings, aget_embeddings
from llama_index.legacy.llms.konko_utils import to_openai_message_dicts
from llama_index.llms.openai import OpenAI as Llama_OpenAI
from llama_index.llms.openai.base import llm_retry_decorator
from llama_index_client import MessageRole
from openai import OpenAI as LlamaOpenAI, AsyncOpenAI as LlamaAsyncOpenAI, APIError
from openai._types import Headers
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall, ChoiceDelta, ChatCompletionChunk
from pydantic import Field
from requests import RequestException
from requests_toolbelt import MultipartEncoder

from app.common.contexts import query_embedding_context, TraceContext
from app.utils.metric_util import increment_counter_with_tag
from common.helper.exception import FileNotFoundException
from init.settings import user_logger, OPENAPI
from bella_rag.llm.types import RerankResponse, dict_to_sensitive, ChatMessage, ChatResponse, Sensitive
from bella_rag.utils.file_util import create_standard_dom_tree_from_json
from bella_rag.utils.openapi_util import openapi_modelname_to_contextsize, openapi_is_function_calling_model, \
    openapi_model_supported_params
from bella_rag.utils.trace_log_util import trace
from bella_rag.utils.user_util import get_user_info

ChatResponseGen = Generator[ChatResponse, None, None]
TokenGen = Generator[Union[str, APIError, List[Sensitive]], None, None]
COMPLETION_ERROR_KEY = 'completion_error'

logger = user_logger


class OpenAI(LlamaOpenAI):
    @property
    def auth_headers(self) -> dict[str, str]:
        api_key = self.api_key
        return {"Authorization": api_key}

    @property
    def default_headers(self):
        return {
            **super().default_headers,
            # 添加trace头
            TRACE_ID: TraceContext.trace_id,
            **self._custom_headers,
        }


class AsyncOpenAI(LlamaAsyncOpenAI):
    @property
    def auth_headers(self) -> dict[str, str]:
        api_key = self.api_key
        return {"Authorization": api_key}

    @property
    def default_headers(self):
        return {
            **super().default_headers,
            # 添加trace头
            TRACE_ID: TraceContext.trace_id,
            **self._custom_headers,
        }


def get_embedding(client: OpenAI, texts: List[str], model: str) -> List[Embedding]:
    return get_embeddings(client, texts, model, user=get_user_info())


async def aget_embedding(client: AsyncOpenAI, texts: List[str], model: str) -> List[Embedding]:
    return await aget_embeddings(client, texts, model, user=get_user_info())


def stream_completion_response_to_tokens(
        completion_response_gen: CompletionResponseGen,
) -> TokenGen:
    """Convert a stream completion response to a stream of tokens."""

    def gen() -> TokenGen:
        for response in completion_response_gen:
            if response.additional_kwargs.get(COMPLETION_ERROR_KEY) is not None:
                yield response.additional_kwargs.get(COMPLETION_ERROR_KEY)
            elif response.message and response.message.sensitives:
                yield response.message.sensitives
            else:
                yield response.delta or ""

    return gen()


def stream_chat_response_to_tokens(
        chat_response_gen: ChatResponseGen,
) -> TokenGen:
    """Convert a stream completion response to a stream of tokens."""

    def gen() -> TokenGen:
        for response in chat_response_gen:
            if response.additional_kwargs.get(COMPLETION_ERROR_KEY) is not None:
                yield response.additional_kwargs.get(COMPLETION_ERROR_KEY)
            elif response.message and response.message.sensitives:
                yield response.message.sensitives
            else:
                yield response.delta or ""

    return gen()


class OpenAPIEmbedding(BaseEmbedding):
    api_key: str = Field(description="The OpenAI API key.")
    _client: Optional[OpenAI] = PrivateAttr()
    _aclient: Optional[AsyncOpenAI] = PrivateAttr()
    user: str = Field(default_factory=get_user_info, description="user")
    model_dimension: int = Field(description="embedding模型维数")

    def __init__(self, model: str, api_key: str, embedding_batch_size: int, model_dimension: int = 1024, **kwargs):
        super().__init__(
            model_name=model,
            embed_batch_size=embedding_batch_size,
            api_key=api_key,
            model_dimension=model_dimension,
            **kwargs,
        )
        self._client = None
        self._aclient = None

    def _get_query_embedding(self, query: str) -> Embedding:
        if TraceContext.is_mock_request:
            time.sleep(random.uniform(0.1, 0.3))
            logger.info(f'mock request _get_query_embedding, query: {query}')
            return [random.uniform(0, 1) for _ in range(self.model_dimension)]
        client = self._get_client(self.api_key)
        embedding = get_embedding(client, [query], self.model_name)[0]
        query_embedding_context.set(embedding)
        return embedding

    async def _aget_query_embedding(self, query: str) -> Embedding:
        if TraceContext.is_mock_request:
            time.sleep(random.uniform(0.1, 0.3))
            logger.info(f'mock request _aget_query_embedding, query: {query}')
            return [random.uniform(0, 1) for _ in range(self.model_dimension)]
        aclient = self._get_aclient(self.api_key)
        embeddings = await aget_embedding(aclient, [query], self.model_name)
        return embeddings[0]

    def _get_text_embedding(self, text: str) -> Embedding:
        if TraceContext.is_mock_request:
            time.sleep(random.uniform(0.1, 0.3))
            logger.info(f'mock request _get_text_embedding, query: {text}')
            return [random.uniform(0, 1) for _ in range(self.model_dimension)]
        client = self._get_client(self.api_key)
        return get_embedding(client, [text], self.model_name)[0]

    def _get_client(self, api_key: str) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(api_key=api_key, base_url=OPENAPI["URL"])
        return self._client

    @trace(step="generate_embeddings", log_enabled=False)
    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get text embeddings.

        By default, this is a wrapper around _get_text_embedding.
        Can be overridden for batch queries.

        """
        if TraceContext.is_mock_request:
            time.sleep(random.uniform(0.2, 1))
            logger.info(f'mock request _get_text_embeddings, query size: {len(texts)}')
            [[random.uniform(0, 1) for _ in range(self.model_dimension)] for _ in range(len(texts))]
        client = self._get_client(self.api_key)
        return get_embeddings(client, texts, self.model_name)

    def _get_aclient(self, api_key: str) -> AsyncOpenAI:
        if self._aclient is None:
            self._aclient = AsyncOpenAI(api_key=api_key, base_url=OPENAPI["URL"])
        return self._aclient


class OpenAPI(Llama_OpenAI):

    @property
    def metadata(self) -> LLMMetadata:
        # openapi全都走chat
        return LLMMetadata(
            context_window=openapi_modelname_to_contextsize(self._get_model_name()),
            num_output=self.max_tokens or -1,
            is_chat_model=True,
            is_function_calling_model=openapi_is_function_calling_model(
                model=self._get_model_name()
            ),
            model_name=self.model,
        )

    def predict(
            self,
            prompt: BasePromptTemplate,
            model: Optional[str] = None,
            max_tokens: Optional[int] = None,
            extra_headers: Optional[Headers] = None,
            **prompt_args: Any,
    ) -> str:
        dispatcher.event(
            LLMPredictStartEvent(template=prompt, template_args=prompt_args)
        )
        self._log_template_data(prompt, **prompt_args)

        if self.metadata.is_chat_model:
            messages = self._get_messages(prompt, **prompt_args)
            chat_response = self.chat(messages, model=model if model else self.model, max_tokens=max_tokens,
                                      extra_headers=extra_headers)
            output = chat_response.message.content or ""
        else:
            formatted_prompt = self._get_prompt(prompt, **prompt_args)
            response = self.complete(formatted_prompt, formatted=True)
            output = response.text
        parsed_output = self._parse_output(output)
        dispatcher.event(LLMPredictEndEvent(output=parsed_output))
        return parsed_output

    def stream(
            self,
            prompt: BasePromptTemplate,
            model: [str] = None,
            max_tokens: Optional[int] = None,
            extra_headers: Optional[Headers] = None,
            **prompt_args: Any,
    ) -> TokenGen:
        self._log_template_data(prompt, **prompt_args)

        dispatcher.event(
            LLMPredictStartEvent(template=prompt, template_args=prompt_args)
        )
        if self.metadata.is_chat_model:
            messages = self._get_messages(prompt, **prompt_args)
            chat_response = self.stream_chat(messages, model=model if model else self.model, max_tokens=max_tokens,
                                             extra_headers=extra_headers)
            stream_tokens = stream_chat_response_to_tokens(chat_response)
        else:
            formatted_prompt = self._get_prompt(prompt, **prompt_args)
            stream_response = self.stream_complete(formatted_prompt, formatted=True)
            stream_tokens = stream_completion_response_to_tokens(stream_response)

        if prompt.output_parser is not None or self.output_parser is not None:
            raise NotImplementedError("Output parser is not supported for streaming.")

        return stream_tokens

    def _get_client(self) -> OpenAI:
        if not self.reuse_client:
            return OpenAI(**self._get_credential_kwargs())

        if self._client is None:
            self._client = OpenAI(**self._get_credential_kwargs())
        return self._client

    def _get_aclient(self) -> AsyncOpenAI:
        if not self.reuse_client:
            return AsyncOpenAI(**self._get_credential_kwargs(is_async=True))

        if self._aclient is None:
            self._aclient = AsyncOpenAI(**self._get_credential_kwargs(is_async=True))
        return self._aclient

    @trace("completion_messages")
    def _get_messages(
            self, prompt: BasePromptTemplate, **prompt_args: Any
    ) -> List[ChatMessage]:
        query_str = prompt_args.get("query_str")
        system_format = prompt.format(llm=self, roleInfo=self.system_prompt, **prompt_args)
        messages = [ChatMessage(role=MessageRole.SYSTEM, content=system_format, additional_kwargs={})]
        if query_str:
            messages.append(ChatMessage(role=MessageRole.USER, content=query_str, additional_kwargs={}))
        logger.info(f"completion messages : {messages}")
        return messages

    def _get_model_kwargs(self, **kwargs: Any) -> Dict[str, Any]:
        supported = openapi_model_supported_params(self._get_model_name())

        # 构建基础参数
        model_kwargs = {
            "model": self.model,
            "user": get_user_info()
        }

        if supported['temperature']:
            model_kwargs['temperature'] = self.temperature

        all_params = {**kwargs, **self.additional_kwargs}
        for key, value in all_params.items():
            if key not in ('max_tokens', 'top_p') or supported[key]:
                model_kwargs[key] = value

        logger.info(f"Model: {self.model}, Final kwargs: {model_kwargs}")
        return model_kwargs

    @llm_retry_decorator
    def _stream_chat(
            self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        client = self._get_client()
        message_dicts = to_openai_message_dicts(messages)

        def gen() -> ChatResponseGen:
            content = ""
            tool_calls: List[ChoiceDeltaToolCall] = []

            is_function = False
            try:
                for response in client.chat.completions.create(
                        messages=message_dicts,
                        stream=True,
                        **self._get_model_kwargs(**kwargs),
                ):
                    response = cast(ChatCompletionChunk, response)
                    sensitives = response.dict().get('sensitives', [])
                    if sensitives:
                        yield ChatResponse(
                            message=ChatMessage(
                                role='assistant',
                                content='',
                                sensitives=[dict_to_sensitive(sensitive) for sensitive in sensitives],
                                additional_kwargs={},
                            ),
                            delta='',
                            additional_kwargs={}
                        )
                        continue

                    # 如果流式消息缺失choices，先跳过该包
                    if not response.choices:
                        continue

                    if len(response.choices) > 0:
                        delta = response.choices[0].delta
                    else:
                        if self._is_azure_client():
                            continue
                        else:
                            delta = ChoiceDelta()

                    # check if this chunk is the start of a function call
                    if delta.tool_calls:
                        is_function = True

                    # update using deltas
                    role = delta.role or MessageRole.ASSISTANT
                    content_delta = delta.content or ""
                    content += content_delta

                    additional_kwargs = {}
                    if is_function:
                        tool_calls = self._update_tool_calls(tool_calls, delta.tool_calls)
                        additional_kwargs["tool_calls"] = tool_calls

                    yield ChatResponse(
                        message=ChatMessage(
                            role=role,
                            content=content,
                            additional_kwargs=additional_kwargs,
                        ),
                        delta=content_delta,
                        raw=response,
                        additional_kwargs=self._get_response_token_counts(response),
                    )
            except APIError as e:
                logger.error(f'rag stream request llm error.{e}\\n{traceback.format_exc()}')
                increment_counter_with_tag('rag', 'error_code', e.code)
                yield ChatResponse(
                    message=ChatMessage(
                        role='assistant',
                        content=e.message,
                        additional_kwargs={},
                    ),
                    delta=e.message,
                    additional_kwargs={COMPLETION_ERROR_KEY: e}
                )

        return gen()

    @llm_chat_callback()
    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        chat_response = super()._chat(messages, **kwargs)

        # 提取敏感信息
        if chat_response.message and chat_response.raw:
            chat_message = chat_response.message
            sensitives = chat_response.raw.get('sensitives', [])
            chat_message = ChatMessage(
                role=chat_message.role,
                content=chat_message.content,
                sensitives=[dict_to_sensitive(sensitive) for sensitive in sensitives],
                additional_kwargs=chat_message.additional_kwargs,
            )
            chat_response.message = chat_message
        return chat_response


'''
能力点暂时还没注册到openapi上，先简单封装
'''


class Rerank:
    model: str

    api_base: str

    def __init__(self, api_base: str, model):
        self.api_base = api_base
        self.model = model

    def rerank(self, query: str, docs: List[str]) -> RerankResponse:
        url = self.api_base.format(model=self.model)
        data = {
            "model": self.model,
            "query": query,
            "documents": docs,
            "max_length": 1024
        }
        response = requests.post(url, json=data, timeout=(30, 60))  # 连接超时30秒，读取超时60秒
        response.raise_for_status()
        return RerankResponse(**response.json())


class FileAPIClient:
    """
    file api封装client
    """

    def __init__(self, ak: str, base_url: str):
        """
        初始化FileAPI客户端
        """
        self.ak = ak
        self.base_url = base_url

    def _get_headers(self) -> dict:
        """获取通用请求头"""
        return {'Authorization': f'{self.ak}'}

    def file_content(self, file_id: str) -> BinaryIO:
        """
        下载文件内容到输出流

        :param file_id: 文件ID
        :raises: FileNotFoundException 当文件不存在时
        :raises: RequestException 当请求失败时
        """
        stream = BytesIO()
        url = f"{self.base_url}/files/{file_id}/content"

        try:
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 404:
                raise FileNotFoundException(f"File {file_id} not found")
            response.raise_for_status()

            stream.write(response.content)
            stream.flush()
            return stream
        except RequestException as e:
            logger.error(f"Download file failed: {str(e)}")
            raise

    def domtree_content(self, file_id: str) -> BinaryIO:
        """
        下载domtree文件内容到输出流

        :param file_id: domtree文件ID
        :raises: FileNotFoundException 当文件不存在时
        :raises: RequestException 当请求失败时
        """
        stream = BytesIO()
        url = f"{self.base_url}/files/{file_id}/dom-tree/content"

        try:
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 404:
                raise FileNotFoundException(f"File {file_id} not found")
            response.raise_for_status()

            stream.write(response.content)
            stream.flush()
            return stream
        except RequestException as e:
            logger.error(f"Download file failed: {str(e)}")
            raise

    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        获取文件元信息
        """
        url = f"{self.base_url}/files/{file_id}"

        try:
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 404:
                raise FileNotFoundException(f"file {file_id} not found")

            response.raise_for_status()
            return response.json()

        except RequestException as e:
            logger.error(f"Get file info failed: {str(e)}")
            return None

    def update_processing_status(
            self,
            status: str,
            percent: int,
            file_id: str,
            message: str,
            postprocessor_name: str,
    ):
        """
        更新文件处理进度
        """
        if not file_id or not postprocessor_name:
            return

        url = f"{self.base_url}/files/{file_id}/progress/{postprocessor_name}"

        try:
            requests.post(
                url,
                json={
                    "status": status,
                    "percent": percent,
                    "message": message
                },
                headers=self._get_headers()
            )
        except RequestException as e:
            logger.error(f"Update processing status failed: {str(e)}")

    def batch_get_files(
            self,
            file_ids: List[str],
            get_url: bool = False,
            expires: int = 3600
    ) -> List[Dict]:
        """
        批量获取文件信息
        """
        url = f"{self.base_url}/files/list"

        try:
            response = requests.post(
                url,
                json={
                    "file_ids": file_ids,
                    "get_url": get_url,
                    "expires": expires
                },
                headers=self._get_headers()
            )
            return response.json() if response.status_code == 200 else []
        except RequestException as e:
            logger.error(f"Batch get files failed: {str(e)}")
            return []

    def upload_file(self, file_data: bytes, file_name: str, purpose: str,
                    metadata: Optional[Dict[str, Any]] = None):
        """上传文件到file-api"""
        try:
            fields = {
                'purpose': purpose,
                'file': (file_name, file_data),
            }
            if metadata:
                fields['metadata'] = metadata
            # 创建 MultipartEncoder
            multipart_data = MultipartEncoder(
                fields=fields
            )

            # 设置请求头
            headers = self._get_headers()
            headers.update({
                'Content-Type': multipart_data.content_type,
                'Accept': 'application/json'
            })

            # 发送请求
            response = requests.post(f"{self.base_url}/files", headers=headers, data=multipart_data)
            # 返回响应体
            return response.json()
        except RequestException as e:
            logger.error(f"Update file: {file_name} failed: {str(e)}")
            return None

    def file_url(self, file_id: str, preview_url: Optional[bool] = False, timeout: Optional[int] = None) -> str:
        try:
            url_path = "/preview_url" if preview_url else "/url"
            url = f"{self.base_url}/files/{file_id}{url_path}"
            if timeout:
                url += f'?seconds_duration={timeout}'

            response = requests.get(url, headers=self._get_headers())

            if response.status_code == 404:
                raise FileNotFoundException(f"file {file_id} not found")

            response.raise_for_status()
            return response.json().get('url', '')
        except RequestException as e:
            logger.error(f"get file url failed, file_id: {file_id} {str(e)}")
            return ""

    def delete_file(self, file_id: str):
        url = f"{self.base_url}/files/{file_id}"

        try:
            response = requests.delete(url, headers=self._get_headers())
            if response.status_code == 404:
                raise FileNotFoundException(f"file {file_id} not found")

            response.raise_for_status()
            return response.json()

        except RequestException as e:
            logger.error(f"delete file info failed: {str(e)}")
            return None

    def parse_pdf_from_json(self, file_id: str) -> StandardDomTree:
        """
        获取JSON数据并转换为StandardDomTree
        """
        try:
            user_logger.info(f"start parse PDF domtree from JSON for file_id: {file_id}")
            stream = self.domtree_content(file_id)

            # 读取流内容并解析JSON
            stream.seek(0)  # 确保从头开始读取
            json_content = stream.read().decode('utf-8')

            if not json_content.strip():
                raise ValueError("Empty JSON content received from FileAPIClient" + file_id)

            json_data = json.loads(json_content)
            user_logger.info(f"Successfully loaded JSON data, children count: {len(json_data.get('children', []))}")

            # 直接从JSON创建StandardDomTree
            standard_dom_tree = create_standard_dom_tree_from_json(json_data)
            user_logger.info(
                f"Successfully created StandardDomTree with {len(standard_dom_tree.root.children)} children")

            return standard_dom_tree

        except json.JSONDecodeError as e:
            user_logger.error(f"Failed to parse JSON content: {str(e)}")
            raise RuntimeError(f"Invalid JSON format from FileAPIClient: {str(e)}")
        except Exception as e:
            user_logger.error(f"Failed to parse PDF from JSON for file_id {file_id}: {str(e)}")
            raise RuntimeError(f"Failed to parse PDF from JSON: {str(e)}")

    def get_file_ids_by_space(self, space: str) -> List[str]:
        """
        获取指定space下所有的file_ids
        """
        url = f"{self.base_url}/files/"

        headers = self._get_headers()
        headers['X-BELLA-SPACE-CODE'] = space

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            if 'data' in data and isinstance(data['data'], list):
                return [file['id'] for file in data['data']]
            else:
                return []

        except RequestException as e:
            logger.error(f"get file ids by space failed: {str(e)}")
            return []

    def get_file_ids_by_ancestor(self, ancestor: str) -> List[str]:
        """
        获取指定ancestor下面所有的file_ids
        """
        url = f"{self.base_url}/files/find?type=file"
        files = {'ancestor_id': (None, ancestor)}
        headers = self._get_headers()

        try:
            response = requests.get(
                url,
                files=files,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            if 'data' in data and isinstance(data['data'], list):
                return [file['id'] for file in data['data']]
            else:
                return []

        except RequestException as e:
            logger.error(f"get file ids by ancestor failed: {str(e)}")
            return []


    def get_docx_file_pdf_id(self, docx_file_id: str) -> str:
        try:
            file_info = self.get_file_info(docx_file_id)
            if file_info is None or 'pdf_file_id' not in file_info:
                return ""
            return str(file_info.get('pdf_file_id'))
        except FileNotFoundException:
            return ""


    def file_domtree(self, file_id: str) -> dict:
        """
        获取文件的domtree
        """
        url = f"{self.base_url}/files/{file_id}/dom-tree/content"
        try:
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 404:
                raise FileNotFoundException(f"File {file_id} not found")
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.error(f"Download file failed: {str(e)}")
            raise

    def decode_resource_id(self, resource_id: str) -> Dict[str, str]:
        """
        解析resource_id, 返回包含id和type的字典
        """
        resource_type = 'directory' if resource_id.endswith('-d') else 'file'
        return {'id': resource_id, 'type': resource_type}

    def decode_resource_ids(self, resource_ids: List[str]) -> Tuple[List[str], List[str]]:
        """
        将resource_id列表分类为文件和目录列表
        """
        file_ids = []
        dir_ids = []

        for resource_id in resource_ids:
            resource_info = self.decode_resource_id(resource_id)
            if resource_info['type'] == 'directory':
                dir_ids.append(resource_id)
            else:
                file_ids.append(resource_id)

        return file_ids, dir_ids