from typing import Optional

import requests
import json

from app.client.oauth_client import OauthClient
from init.settings import OAUTH

oauth_client = OauthClient(OAUTH["client_id"], OAUTH["client_secret"], OAUTH["url"])

def get_header(uc_id):
    token = oauth_client.get_access_token()
    token_str = f"{token['token_type']} {token['access_token']}"
    header = {
        "ucId": uc_id,
        "Authorization": token_str,
        "Content-Type": "application/json"
    }
    return header


def user_batch(usercodes: Optional[str] = None, ids: Optional[str] = None):
    if usercodes:
        params = f"?usercodes={','.join(usercodes)}"
    else:
        params = f"?ids={','.join(ids)}"

    headers = get_header("29406069")
    response = requests.get(OAUTH["url"] + '/uc/ehr/user/batch' + params, headers=headers)

    if response.status_code == 200:
        return json.loads(response.text)
    else:
        response.raise_for_status()