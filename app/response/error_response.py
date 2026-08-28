from django.http import HttpResponse
from openai import APIError, APITimeoutError

from app.response.rag_response import OpenApiError
from common.helper import ApiReturn


UPSTREAM_TIMEOUT_MESSAGE = "Embedding service request timed out."
UPSTREAM_ERROR_MESSAGE = "Upstream service request failed."


def create_timeout_error() -> OpenApiError:
    return OpenApiError(
        message=UPSTREAM_TIMEOUT_MESSAGE,
        body={
            "code": ApiReturn.CODE_UPSTREAM_TIMEOUT,
            "type": "upstream_timeout",
            "retryable": True,
        },
    )


def create_upstream_error(error: APIError) -> OpenApiError:
    status_code = getattr(error, "status_code", None)
    return OpenApiError(
        message=UPSTREAM_ERROR_MESSAGE,
        body={
            "code": status_code or 502,
            "type": "upstream_error",
            "retryable": status_code in {408, 429} or status_code is None or status_code >= 500,
        },
    )


def create_http_error_response(error: Exception, default_code: int = ApiReturn.CODE_INNER_CODE,
                               default_type: str = "internal_error", status: int = 500) -> HttpResponse:
    if isinstance(error, APITimeoutError):
        response_error = create_timeout_error()
        return HttpResponse(response_error.json_response(), status=504)
    if isinstance(error, APIError):
        response_error = create_upstream_error(error)
        response_status = getattr(error, "status_code", None) or 502
        return HttpResponse(response_error.json_response(), status=response_status)

    response_error = OpenApiError(
        message="Internal server error.",
        body={"code": default_code, "type": default_type},
    )
    return HttpResponse(response_error.json_response(), status=status)


def create_stream_error(error: Exception) -> dict:
    if isinstance(error, APITimeoutError):
        return {
            "code": ApiReturn.CODE_UPSTREAM_TIMEOUT,
            "type": "upstream_timeout",
            "message": UPSTREAM_TIMEOUT_MESSAGE,
            "retryable": True,
        }
    if isinstance(error, APIError):
        status_code = getattr(error, "status_code", None)
        return {
            "code": status_code or 502,
            "type": "upstream_error",
            "message": UPSTREAM_ERROR_MESSAGE,
            "retryable": status_code in {408, 429} or status_code is None or status_code >= 500,
        }
    return {
        "code": ApiReturn.CODE_INNER_CODE,
        "type": "internal_error",
        "message": "Internal server error.",
        "retryable": False,
    }


def create_stream_api_error(error: Exception) -> OpenApiError:
    stream_error = create_stream_error(error)
    return OpenApiError(message=stream_error["message"], body=stream_error)
