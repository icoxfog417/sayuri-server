from datetime import datetime
from datetime import timedelta
from sayuri_model import Recognizer


class TimeRecognizer(Recognizer):

    def __init__(self):
        #interval = timedelta(hours=1)
        interval = timedelta(seconds=10)
        super().__init__(interval)

    def recognize(self):
        now = datetime.now()

        if now.hour > 17:
            return "night"
        elif now.hour > 12:
            return "daytime"
        elif now.hour > 6:
            return "morning"
        elif now.hour > 0:
            return "night"


class MessageRecognizer(Recognizer):

    def __init__(self):
        super().__init__(None)

    def recognize(self):
        return None


class TemperatureRecognizer(Recognizer):

    def __init__(self):
        interval = timedelta(hours=1)
        super().__init__(interval)

    def recognize(self):
        return 25
