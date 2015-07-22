import os
import json
from collections import namedtuple


class Environment():
    __ENVS = {}

    def __init__(self):
        if not self.__ENVS:
            self.__ENVS = self.__load()

    def __load(self):
        keys = ["SECRET_KEY", "REDIS_URL", "FACE_API_KEY", "FACE_API_SECRET", "FACE_API_NAMESPACE", "FACE_API_USER_ID"]
        envs = {}

        envs_file = os.path.join(os.path.dirname(__file__), "../envs.json")
        if os.path.isfile(envs_file):
            with open(envs_file) as f:
                envs = json.load(f)
        else:
            for k in keys:
                envs[k] = os.getenv(k)
                if k == "REDIS_URL" and not envs[k]:
                    for r in ["REDISCLOUD_URL", "REDISTOGO_URL"]:
                        if os.getenv(r):
                            envs[k] = os.getenv(r)

        return envs

    def secret_key(self):
        return self.__ENVS["SECRET_KEY"]

    def redis_url(self):
        return self.__ENVS["REDIS_URL"]

    def face_api_keys(self):
        FaceApiKey = namedtuple("FaceApiKey", ["key", "secret", "namespace", "user_id"])
        f_key = FaceApiKey(self.__ENVS["FACE_API_KEY"],
                           self.__ENVS["FACE_API_SECRET"],
                           self.__ENVS["FACE_API_NAMESPACE"],
                           self.__ENVS["FACE_API_USER_ID"])

        return f_key
