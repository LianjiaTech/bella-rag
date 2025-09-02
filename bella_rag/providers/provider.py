import io
import uuid

from common.helper.exception import BusinessError
from common.tool.s3_tool import S3
from init.settings import user_logger


class ImageProvider:
    s3: S3  # 使用s3做存储

    def upload(self, image: bytes) -> str:
        """上传图片并返回唯一标识"""
        image_type = self.get_image_type(image)
        file_name = f"{str(uuid.uuid4())}.{image_type}"
        if image_type != 'Unknown':
            image_info = self.s3.upload_file(io.BytesIO(image), file_name)
            if not image_info:
                user_logger.warn(f'图片上传失败！file_name : {file_name}')
                raise BusinessError("图片上传失败！")
            return file_name
        else:
            raise BusinessError("不支持的文件类型！")

    def download(self, file_key: str) -> str:
        """获取文件url"""
        return self.s3.get_image_url_sign(file_key, 7 * 24 * 60 * 60)

    @staticmethod
    def get_image_type(byte_stream):
        if byte_stream.startswith(b'\xFF\xD8\xFF'):
            return 'JPEG'
        elif byte_stream.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'PNG'
        elif byte_stream.startswith(b'GIF87a') or byte_stream.startswith(b'GIF89a'):
            return 'GIF'
        elif byte_stream.startswith(b'BM'):
            return 'BMP'
        elif byte_stream.startswith(b'\x49\x49\x2A\x00') or byte_stream.startswith(b'\x4D\x4D\x00\x2A'):
            return 'TIFF'
        elif byte_stream.startswith(b'\x00\x00\x01\x00'):
            return 'ICO'
        elif byte_stream.startswith(b'\x52\x49\x46\x46') and byte_stream[8:12] == b'WEBP':
            return 'WEBP'
        else:
            return 'Unknown'

    def enable(self):
        return self.s3 is not None
