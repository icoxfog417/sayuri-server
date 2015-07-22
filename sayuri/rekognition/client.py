import urllib.request
import urllib.parse
import json


class Client(object):
    API_HOME = "https://rekognition.com/func/api/"

    def __init__(self, api_key, api_secret, name_space="demo_project", user_id="demo_user"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.name_space = name_space
        self.user_id = user_id

    def face_recognize(self, image_url, **kwargs):
        parameters = self.__make_initial_parameters()
        jobs = "face_recognize"
        for op in kwargs:
            if kwargs[op]:
                jobs += ("_" + op)

        parameters.update({"jobs": jobs, "base64": image_url})
        return self.__request(parameters)

    def __make_initial_parameters(self):
        return {
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "name_space": self.name_space,
            "user_id": self.user_id
        }

    @classmethod
    def __request(cls, parameters):
        p = urllib.parse.urlencode(parameters)
        p = p.encode("utf-8")

        request = urllib.request.Request(cls.API_HOME, p)
        response = urllib.request.urlopen(request)
        content = response.read()
        obj = json.loads(content.decode("utf-8"))
        return obj
