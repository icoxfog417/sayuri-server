import unittest
import os
import base64
import secret_settings
import rekognition


class TestRekognition(unittest.TestCase):

    def test_read_image(self):
        encoded = self.__read_image("persons.jpg")
        self.assertTrue(encoded)

    def test_face_recognize(self):
        client = self.__create_client()
        image = self.__read_image("persons.jpg")
        result = client.face_recognize(image)
        self.assertEqual(result.usage.status, "Succeed.")

    def __create_client(self):
        client = rekognition.Client(secret_settings.FACE_API_KEY,
                                    secret_settings.FACE_API_SECRET,
                                    secret_settings.FACE_API_NAMESPACE,
                                    secret_settings.FACE_API_USER_ID)
        return client

    def __read_image(self, test_file_name):
        path = os.path.join(os.path.dirname(__file__), "images\\" + test_file_name)
        encoded = ""
        with open(path, "rb") as file:
            encoded = base64.b64encode(file.read())

        return encoded
