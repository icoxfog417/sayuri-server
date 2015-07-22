import unittest
import os
import base64
from sayuri import rekognition


class TestRekognition(unittest.TestCase):

    def test_read_image(self):
        encoded = self.__read_image("persons.jpg")
        self.assertTrue(encoded)

    def test_face_recognize(self):
        client = self.__create_client()
        image = self.__read_image("persons.jpg")
        result = client.face_recognize(image)
        self.assertTrue("usage" in result)
        self.assertTrue("status" in result["usage"])
        self.assertEqual(result["usage"]["status"], "Succeed.")

    def __create_client(self):
        from sayuri.env import Environment
        key = Environment().face_api_keys()
        client = rekognition.Client(key.key, key.secret, key.namespace, key.user_id)
        return client

    def __read_image(self, test_file_name):
        path = os.path.join(os.path.dirname(__file__), "images\\" + test_file_name)
        encoded = ""
        with open(path, "rb") as file:
            encoded = base64.b64encode(file.read())

        return encoded
