import json
from typing import List, Optional

import httpx
from openai import APIError

from bella_rag.llm.types import Sensitive


class RagStreamSensitive:
    def __init__(self, id: str, sensitives: List[Sensitive], object: str = "message.sensitives"):
        self.id = id
        self.object = object
        self.sensitives = sensitives

    def json_response(self):
        response_data = {
            'id': self.id,
            'object': self.object,
            'sensitives': [
                sensitive.json_response()
                for sensitive in self.sensitives
            ]
        }
        return response_data

    def __repr__(self):
        return f"RagStreamSensitive(id={self.id}, object={self.object}, sensitives={self.sensitives})"


# 定义openapi error结构体
class OpenApiError(APIError):

    def __init__(self, message: str, *, body: Optional[object]) -> None:
        super().__init__(message, httpx.Request("", ""), body=body)

    def __repr__(self):
        return f"OpenApiError(type={self.type}, message={self.message})"

    def json_response(self):
        error_dict = {
            "message": self.message,
            "code": self.code,
            "type": self.type
        }
        return json.dumps({"error": error_dict})


def create_response(code, message, data):
    return {
        "code": code,
        "message": message,
        "data": data
    }
