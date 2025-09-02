from django.db.backends.mysql.base import DatabaseWrapper as BaseDatabaseWrapper
from django.utils.asyncio import async_unsafe


class DatabaseWrapper(BaseDatabaseWrapper):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @async_unsafe
    def ensure_connection(self):
        """
            原django实现只校验了连接是否是None，并没有对连接进行是否存活的判断。
            而connects['default']是从线程里面拿的连接，不会是None但会失效，特别是对于kafka消费来说。
            故加入此检查如果连接有问题则新建
        """
        super().ensure_connection()
        if self.connection is not None:
            try:
                self.connection.ping()
            except self.connection.OperationalError:
                # 连接无效，需要重新建立
                self.close()
                self.connect()
