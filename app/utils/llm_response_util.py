import json
from typing import Union


def get_response_json_str(response_str: str) -> Union[str, None]:
    response_str = response_str.strip()
    if not response_str:
        return None
    if "```json" in response_str:
        s1 = response_str.split("```json")[1]
        s2 = s1.split("```")[0]
        return s2.strip()
    else:
        try:
            json.dumps(json.loads(response_str), ensure_ascii=False, indent=None)
        except ValueError:
            return response_str
        return response_str

