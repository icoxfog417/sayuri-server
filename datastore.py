import os
import redis
import secret_settings


class Datastore(object):

    def __init__(self, *args):
        self.redis_url = os.getenv('REDISCLOUD_URL', secret_settings.REDIS_URL)
        self.connection = redis.StrictRedis.from_url(self.redis_url, decode_responses=True)
        self.schema = list(args)  # schema is attached to every key

    @classmethod
    def create(cls, *args):
        return Datastore()

    def __format_key(self, key):
        return ":".join(self.schema + [key])

    def store(self, key, value, nx=False):
        k = self.__format_key(key)
        if type(value) == dict:
            if not nx or (nx and self.connection.exists(key)):
                self.connection.hmset(k, value)
        else:
            self.connection.set(k, value, nx=nx)

    def get(self, key, field=None):
        k = self.__format_key(key)
        if field:
            return self.connection.hget(k, field)
        else:
            return self.connection.get(k)

    def delete(self, *key):
        ks = [self.__format_key(k) for k in key]
        return self.connection.delete(ks)

    def delete_from_list(self, list_name, count, is_from_right=True):
        for i in range(count):
            if is_from_right:
                self.connection.rpop(list_name)
            else:
                self.connection.lpop(list_name)

    def store_to_list(self, list_name, *value):
        ln = self.__format_key(list_name)
        self.connection.lpush(ln, *value)

    def get_list(self, list_name, index=0):
        ln = self.__format_key(list_name)
        result = self.connection.lrange(ln, 0, index)
        return result

    def get_single(self, list_name):
        result = self.get_list(list_name, 0)
        if result:
            return result[0]
        else:
            return ""

    def trim_list(self, list_name, length=-1):
        ln = self.__format_key(list_name)
        if length == -1:
            return self.connection.delete(ln)
        else:
            return self.connection.ltrim(ln, 0, length)


class KeyValue(object):

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def to_dict(self):
        return {"key": self.key, "value": self.value}
