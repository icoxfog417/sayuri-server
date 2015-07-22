import unittest
import time
from datetime import timedelta
from threading import Timer
import math
from sayuri import framework


def scheduler(interval, callback):
    Timer(interval.seconds, callback).start()


def sender(message):
    print(message)


class TestRecognizer(framework.Recognizer):

    def __init__(self):
        interval = timedelta(seconds=1)
        super().__init__(interval)
        self.counter = 0

    def recognize(self, message):
        if message:
            self.counter = int(message)
        else:
            self.counter += 1
        return self.counter


class TestAction(framework.Action):
    def __init__(self, border=1):
        super().__init__(TestRecognizer)
        self.border = border
        self.over = False

    def execute(self, data, observer):
        counter = int(data[TestRecognizer.key()][-1])
        if counter >= self.border:
            self.over = True


class TestRecognize(unittest.TestCase):

    def test_schedule(self):
        recognizer = TestRecognizer()
        tr = lambda: recognizer.recognize(0)
        scheduler(recognizer.interval, tr)

        wait_time = 1.1
        time.sleep(wait_time)
        self.assertEqual(math.floor(wait_time), recognizer.counter)

    def test_observer(self):
        observer = framework.RecognitionObserver(scheduler, sender)
        action = TestAction(4)
        recognizer = TestRecognizer()
        observer.set_recognizer(recognizer)
        observer.set_action(action)

        cnt = 0
        observer.run()
        wait_time = 2.2
        fixed = 5
        time.sleep(wait_time)
        cnt = recognizer.counter
        observer.get_recognizer(TestRecognizer).invoke(fixed)
        observer.stop()
        self.assertEqual(math.floor(wait_time), cnt)
        self.assertEqual(fixed, recognizer.counter)
        self.assertTrue(action.over)
