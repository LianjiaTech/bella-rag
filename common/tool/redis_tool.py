import redis


class RedisTool(object):
    def __init__(self, host="", port=0, db=0, password=""):
        try:
            self.host = host
            self.port = int(port)
            self.db = int(db)
            self.password = password
        except:
            raise TypeError("<ERROR: port 和 db 必须是数字>")

    def init_redis_conf(self):
        if not hasattr(self, 'pool'):
            self.create_pool()
        self._connection = redis.Redis(connection_pool=self.pool)
        return self

    def connect(self):
        self._connection = redis.Redis(
            host=self.host,
            port=self.port,
            password=self.password,
            db=self.db)
        return self

    def operator_status(func):
        '''get operatoration status
        '''
        def gen_status(*args, **kwargs):
            error, result = None, None
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                result = str(e)
            return result

        return gen_status

    def create_pool(self):
        self.pool = redis.ConnectionPool(
            host=self.host,
            port=self.port,
            password=self.password,
            db=self.db)

    @operator_status
    def set_data(self, key, value, ex=None):
        '''set data with (key, value)
        '''
        return self._connection.set(key, value, ex=ex)

    @operator_status
    def get_data(self, key):
        '''get data by key
        '''
        redisvalue = self._connection.get(key)
        if redisvalue:
            return str(redisvalue, encoding="utf-8")
        else:
            return None

    def get_data_for_data_keyword(self, key):
        '''get data by key
        '''
        get_value = self._connection.get(key)
        if get_value:
            return str(get_value, encoding="utf-8")
        else:
            raise ValueError("EXCEPTION: ERROR: 没有找到key[%s]" % key)

    @operator_status
    def del_data(self, key):
        '''delete cache by key
        '''
        return self._connection.delete(key)

    @operator_status
    def expire_data(self, key, time):
        '''
        设置某个key值的超时时间
        :param key:redis的key值
        :param time: 设置的超时时间 int类型
        :return:
        '''
        return self._connection.expire(key, time)

    def exists_key(self, key):
        '''
        设置某个key值的超时时间
        :param key:redis的key值
        :param time: 设置的超时时间 int类型
        :return:
        '''
        return self._connection.exists(key)

    @operator_status
    def flushall(self):
        '''flush redis
        '''
        return self._connection.flushall()
