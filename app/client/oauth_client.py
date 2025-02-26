import base64
import hmac
import uuid
from _sha2 import sha256
from urllib.error import HTTPError

import requests
import time

class OauthClient:
    client_id: str
    client_secret: str
    url: str

    def __init__(self, client_id, client_secret, url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.url = url

    def get_access_token(self):
        """
        当且仅当code=10000时，代表Token申请成功，非10000都标识申请失败。
        Token申请成功后返回的数据结构(code值固定为10000)：
        {
          "code": 10000,
          "message": "SUCCESS",
          "access_token": "xdsdsdsdfsdfdsf",
          "token_type": "Bearer",
          "expires_in": 216000
        }
        Token申请异常后返回的数据结构(code值是网关返回的全局错误码，可能变）：
        {
          "code": 900003,
          "message": "客户端非法"
        }
        全局错误码请参考：http://doc.shoff.ke.com/v1/doc/new/1269643244/bizcode
        网关接入请参考：http://doc.shtest.ke.com/common-knowledge/oauth/overview.html
        """
        aroute_url = self.url

        # 获取时间戳
        t = time.time()
        timestamp = int(round(t * 1000))
        # print("timestamp====%s" % timestamp)

        # 获取签名
        uuid_str = str(uuid.uuid1())
        data = ("/oauth2/tokenPOSTclient_id=%s&grant_type=client_credentials&nonce=%s&timestamp=%s" %
                (self.client_id, uuid_str, timestamp)).encode('utf-8')
        client_secret = self.client_secret.encode('utf-8')
        signature = base64.urlsafe_b64encode(hmac.new(client_secret, data, digestmod=sha256).digest())
        signature = signature.decode()

        # 获取token
        request_url = aroute_url + "/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        request_body = {"client_id": self.client_id, "grant_type": "client_credentials",
                        "nonce": uuid_str, "timestamp": timestamp, "signature": signature}
        try:
            wb_data = requests.post(request_url, data=request_body, headers=headers, timeout=(8, 15))
            token = wb_data.json()
            if wb_data.status_code < 300:
                token['code'] = 10000
                token['message'] = "SUCCESS"
            else:
                # code为网关返回的全局错误码,messsage为具体提示信息
                raise HTTPError("获取token失败！")
        except requests.exceptions.RequestException as e:
            token = {'code': 900364, 'message': '请求超时！', 'timestamp': timestamp, 'path': '/oauth2/token'}
        return token
