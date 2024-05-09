'''
django-redis的conn建立的redis操作类
'''


class MyRedisCache(object):
    def __init__(self, conn):
        self.conn = conn

    def get_data(self, key):
        retv = self.conn.get(key)
        if retv is None:
            return None
        else:
            return retv

    def set_data(self, key, value, timeout=None):
        if timeout:
            self.conn.set(key, value, ex=timeout)
        else:
            self.conn.set(key, value)

    def set_dict(self, key, dict_value):
        if isinstance(dict_value, dict):
            self.conn.hmset(key, dict_value)
        else:
            raise ValueError("参数2必须是dict类型")

    def get_dict_value_by_key(self, key, dict_key):
        try:
            return self.conn.hget(key, dict_key)
        except:
            return None

    def get_dict_all(self, key):
        try:
            return self.conn.hgetall(key)
        except:
            return None

    def delete_key(self, key):
        return self.conn.delete(key)

    def lpush(self, key, value):
        self.conn.lpush(key, value)

    def brpop(self, key, timeout=60):
        res = self.conn.brpop(key, timeout=timeout)
        if res:
            retkey, retv = res
            if retv is None:
                return None
            else:
                return retv
        else:
            return None

    def incr(self, key, amount=1):
        return self.conn.incr(key, amount)
