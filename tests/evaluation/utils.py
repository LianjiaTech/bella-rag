from llama_index.core.tools import ToolMetadata
from pydantic import BaseModel


def fun():
    pass


class RagToolMetadata(ToolMetadata):

    def get_parameters_dict(self) -> dict:
        return {
            "title": "RagToolInput",
            "type": "object",
            "properties": {
                "query": {
                    "title": "Query",
                    "description": "根据用户的补充信息,重新提取用户的问题。只提取问题，不对用户的问题进行回答，举个例子：问: 我如何学习编程语言。答：你想学哪种语言呢？ 问：python 。最终的输出结果 我如何学习python 。",
                    "type": "string"
                }
            },
            "required": [
                "query"
            ]
        }


def has_call_tool(chat_response) -> bool:
    choices = chat_response.raw.get("choices")
    return choices and len(choices) > 0 and choices[0].finish_reason == "tool_calls"


class Result(BaseModel):
    questions: list
    file_name: str

    def json_response(self):
        response_data = {
            'questions': self.questions,
            'file_name': self.file_name
        }
        return response_data
