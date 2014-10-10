import unittest
import time
from datetime import timedelta
from threading import Timer
import math
import random
import sayuri_model


def scheduler(interval, callback):
    Timer(interval.seconds, callback).start()


def sender(message):
    print(message)


class TestRecognizer(sayuri_model.Recognizer):

    def __init__(self, validation_key=""):
        interval = timedelta(seconds=1)
        super().__init__(interval)
        self.counter = 0
        self.validation_key = validation_key

    def recognize(self):
        self.counter += 1
        return self.validation_key


class TestAction(sayuri_model.Action):
    def __init__(self):
        super().__init__(TestRecognizer)
        self.validation_key = str(random.random())
        self.validated = False

    def execute(self, data):
        self.validated = self.validation_key == data[TestRecognizer.key()]
        return self.validated


class TestRecognize(unittest.TestCase):

    def test_schedule(self):
        recognizer = TestRecognizer()
        scheduler(recognizer.interval, recognizer.recognize)

        wait_time = 1.1
        time.sleep(wait_time)
        self.assertEqual(math.floor(wait_time), recognizer.counter)

    def test_observer(self):
        observer = sayuri_model.RecognitionObserver(scheduler, sender)
        action = TestAction()
        recognizer = TestRecognizer(action.validation_key)
        observer.set_recognizer(recognizer)
        observer.set_action(action)

        observer.run()
        wait_time = 2.2
        time.sleep(wait_time)
        self.assertEqual(math.floor(wait_time), recognizer.counter)
        observer.stop()
