import time
import traceback
import urllib.parse

import boto3
import hashlib
import warnings
from typing import Optional, IO, Dict, Any

from init.settings import user_logger
import json

warnings.filterwarnings('ignore')


class S3(object):
    def __init__(self, config: Dict[str, Any]):
        user_logger.info(f'init s3 client. config: {config}')
        self.access_key = config.get('ak')
        self.secret_access_key = config.get('sk')
        self.region_name = config.get('region_name')
        self.bucket_name = config.get('bucket_name')
        self.endpoint_url = config.get('endpoint')
        self.image_domain = config.get('image_domain')
        try:
            self.session = boto3.session.Session(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region_name
            )
            self.s3_client = self.session.resource('s3', region_name=self.region_name, endpoint_url=self.endpoint_url)
            self.bucket = self.s3_client.Bucket(self.bucket_name)
        except Exception as e:
            user_logger.error(f's3 connect error. msg: {repr(e)}')

    def get_image_url_sign(self, filename: str, expire: int = 3600) -> Optional[str]:
        if not filename:
            return None
        domain = self.image_domain
        path = f'/{self.bucket_name}/{filename}'
        ak = self.access_key
        sk = self.secret_access_key
        ts = int(time.time())

        data = [('ak', ak), ('path', path), ('ts', ts), ('exp', expire)]
        data = sorted(data)

        verify = ''
        for (key, value) in data:
            verify = f"{verify}{key.strip()}={value}&"
        verify = f"{verify}sk={sk}"
        sign = hashlib.md5(verify.encode('utf-8')).hexdigest()
        return f'{domain}{path}?ak={ak}&exp={expire}&ts={ts}&sign={sign}'


    def upload_file(self, file: IO, filename: str, content_type: Optional[str] = None) -> bool:
        """
        上传文件流到S3
        :param file: 文件流对象，如 io.BytesIO
        :param filename: S3中的文件名
        :param content_type: 可选，文件类型
        :return: 上传是否成功
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            self.bucket.upload_fileobj(file, filename, ExtraArgs=extra_args if extra_args else None)
            return True
        except Exception:
            traceback.print_exc()
            return False

    def sign_url(self, url: str, expire_seconds: int = 3600, file_end_point: str = None) -> str:
        """链接重新加签"""
        if not url:
            return url

        # 不具备操作权限的链接不加签
        if f'/{self.bucket_name}' not in url:
            return url

        # 替换 http 为 https
        if url.startswith("http:"):
            url = url.replace("http:", "https:", 1)

        # 替换内网域名为外网域名
        url = url.replace(self.endpoint_url, file_end_point or self.image_domain)

        # 解析 URL
        uri = urllib.parse.urlparse(url)
        host = uri.hostname
        path = uri.path

        # 解码 path
        try:
            decode_path = urllib.parse.unquote(path)
        except Exception:
            decode_path = path

        # 时间戳
        ts = int(time.time())
        # 拼接签名字符串
        sign_builder = f"ak={self.access_key}&exp={expire_seconds}&path={decode_path}&ts={ts}&sk={self.secret_access_key}"
        sign = hashlib.md5(sign_builder.encode('utf-8')).hexdigest()
        params = f"ak={self.access_key}&exp={expire_seconds}&ts={ts}&sign={sign}"

        # 返回带签名的 URL
        signed_url = f"{uri.scheme}://{host}{path}?{params}"
        return signed_url

    def upload_dict_content(self, data: dict, file_key: str) -> str:
        json_data = json.dumps(data)
        self.bucket.Object(file_key).put(Body=json_data)
        return file_key

    def download_dict_content(self, file_key: str) -> dict:
        response = self.bucket.Object(file_key).get()
        return response['Body'].read().decode('utf-8')
    
    def delete_file(self, file_key: str) -> bool:
        """删除字典内容"""
        try:
            self.bucket.Object(file_key).delete()
            user_logger.info(f'Successfully deleted dict content: {file_key}')
            return True
        except Exception as e:
            user_logger.error(f'Failed to delete dict content {file_key}: {repr(e)}')
            traceback.print_exc()
            return False

    def exists_file(self, file_key: str) -> bool:
        """判断字典内容是否存在"""
        try:
            self.bucket.Object(file_key).load()
            user_logger.info(f'Dict content exists: {file_key}')
            return True
        except Exception as e:
            user_logger.info(f'Dict content not exists: {file_key}')
            return False 