from common.tool.s3_tool import S3
from init.settings import S3_CONFIG
from bella_rag.providers.provider import ImageProvider

# 如果s3配置，则初始化图片存储器
s3_storage = S3(S3_CONFIG) if S3_CONFIG.get('endpoint') and S3_CONFIG.get('bucket_name') else None
image_storage_provider = ImageProvider()
image_storage_provider.s3 = s3_storage
