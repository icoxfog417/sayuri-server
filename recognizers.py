from datetime import datetime
from datetime import timedelta
import json
from sayuri_framework import Recognizer, RecognitionObserver
import rekognition
from model import Conference
from datastore import Datastore


class TimeRecognizer(Recognizer):
    PHASE_START = "START"
    PHASE_LIMIT = "PHASE_LIMIT"
    PHASE_CLOSING = "PHASE_CLOSING"
    PHASE_END = "PHASE_END"

    def __init__(self):
        interval = timedelta(seconds=60)
        super().__init__(interval)

    def recognize(self, message):
        conference = Conference.get(self.observer.conference_key)
        delta = Conference.calculate_remained(conference)

        if delta <= 0:
            self.observer.is_continue = False
            return self.PHASE_END
        elif delta <= 3:
            return self.PHASE_LIMIT
        elif delta <= 10:
            return self.PHASE_CLOSING


class FaceDetectIntervalRecognizer(Recognizer):
    def __init__(self):
        interval = timedelta(seconds=10)
        super().__init__(interval)

    def recognize(self, message):
        self.interval = timedelta(seconds=360)
        return True


class FaceRecognizer(Recognizer):

    def __init__(self):
        super().__init__(None)

    def recognize(self, message):
        detected_face = self.face_recognize(message)
        return json.dumps(detected_face)

    def face_recognize(self, base64_images):
        import secret_settings
        client = rekognition.Client(secret_settings.FACE_API_KEY,
                                    secret_settings.FACE_API_SECRET,
                                    secret_settings.FACE_API_NAMESPACE,
                                    secret_settings.FACE_API_USER_ID)

        detecteds = []
        for b64m in base64_images:
            d = client.face_recognize(b64m, gender=True, emotion=True, mouth_open_wide=True, eye_closed=True)
            detecteds.append(d)
        return detecteds


class SayuriRecognitionObserver(RecognitionObserver):

    def __init__(self, schedule_func, send_func, user, conference_key):
        super(SayuriRecognitionObserver, self).__init__(schedule_func, send_func)
        self.user = user
        self.conference_key = conference_key
        self.datastore = Datastore(user, conference_key)
