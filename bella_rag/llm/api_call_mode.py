from typing import Mapping, Optional, Dict


DIRECT_CALL_MODE = "direct"
BILLING_TRANSFER_MODE = "billing_transfer"

SERVICE_CLIENT_HEADER = "X-Service-Client"
EFFECTIVE_API_KEY_CODE_HEADER = "X-Effective-Api-Key-Code"


def build_api_call_headers(
        call_mode: str = DIRECT_CALL_MODE,
        service_client: Optional[str] = None,
        effective_api_key_code: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
) -> Dict[str, str]:
    """Build per-request headers for direct or billing-transfer API calls."""
    headers = dict(extra_headers or {})

    if call_mode == DIRECT_CALL_MODE:
        return headers

    if call_mode != BILLING_TRANSFER_MODE:
        raise ValueError(f"Unsupported OpenAPI call mode: {call_mode}")

    if not service_client:
        raise ValueError("service_client is required for billing-transfer API calls")
    if not effective_api_key_code:
        raise ValueError(
            "UserContext.usage_ak_code is required for billing-transfer API calls"
        )

    headers[SERVICE_CLIENT_HEADER] = service_client
    headers[EFFECTIVE_API_KEY_CODE_HEADER] = effective_api_key_code
    return headers
