# 创建连接池
from redis.connection import ConnectionPool

from init.settings import REDIS_HOST, REDIS_DATABASE, REDIS_PWD, REDIS_PORT

redis_pool = ConnectionPool(
    host=REDIS_HOST,  # Redis服务器地址
    port=REDIS_PORT,  # Redis服务器端口
    password=REDIS_PWD,  # 连接密码（如果有）
    db=REDIS_DATABASE  # 选择数据库
)
