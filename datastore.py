import os
import redis
import secret_settings


class Datastore(object):
    redis_url = ""
    instance = None

    def __init__(self):
        if not Datastore.instance:
            Datastore.redis_url = os.getenv('REDISTOGO_URL', secret_settings.REDIS_URL)
            Datastore.instance = redis.StrictRedis.from_url(self.redis_url, decode_responses=True)

    @classmethod
    def store(cls, key, value, nx=False):
        if type(value) == dict:
            if not nx or (nx and cls.instance.exists(key)):
                cls.instance.hmset(key, value)
        else:
            cls.instance.set(key, value, nx=nx)

    @classmethod
    def get(cls, key, field=None):
        if field:
            return cls.instance.hget(key, field)
        else:
            return cls.instance.get(key)

    @classmethod
    def delete(cls, *key):
        return cls.instance.delete(key)

    @classmethod
    def store_to_list(cls, list_name, *value):
        cls.instance.lpush(list_name, *value)

    @classmethod
    def get_from_list(cls, list_name):
        result = cls.instance.lrange(list_name, 0, 0)
        if result:
            return result[0]
        else:
            return ""

    @classmethod
    def get_range(cls, list_name, index):
        return cls.instance.lrange(list_name, 0, index)

    @classmethod
    def trim_list(cls, list_name, length=-1):
        if length == -1:
            return cls.instance.delete(list_name)
        else:
            return cls.instance.ltrim(list_name, 0, length)


class KeyValue(object):

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def to_dict(self):
        return {"key": self.key, "value": self.value}
