from datetime import datetime
from datastore import Datastore


class Recognizer(object):

    def __init__(self, interval):
        self.interval = interval  # timedelta. when None then not scheduled
        self.value = None
        self.observer = None

    @classmethod
    def key(cls):
        return cls.__name__.lower()

    def set_observer(self, observer):
        self.observer = observer

    def remove_observer(self):
        self.observer = None

    def invoke(self, message=None):

        if not message:
            # recognize and get value
            self.value = self.recognize()
        else:
            self.value = message

        # store value into database
        Datastore().store_to_list(self.key(), self.value)

        # notify to observer that data is updated
        self.observer.notify(self)

    # must override
    def recognize(self):
        # get and return recognized data
        raise Exception("You have to implements recognize method")


class Action(object):

    def __init__(self, *recognizers):
        self.recognizers = recognizers  # recognizer classes

    @classmethod
    def key(cls):
        return cls.__name__.lower()

    def has_recognizer(self, recognizer):
        result = False
        for r in self.recognizers:
            if type(recognizer) == r:
                result = True

        return result

    def trigger(self):
        data = {}
        for r in self.recognizers:
            key = r.key()
            value = Datastore().get_from_list(key)
            data.update({key: value})

        result = self.execute(data)
        if result:
            message = self.__make_message(result)
            self.__store_log(message)
            return message
        else:
            return None

    # must override
    def execute(self, data):
        # execute some action. it returns message object for chat bot(user __make_message).
        raise Exception("You have to implements execute method")

    @classmethod
    def _get_timestamp(cls):
        return datetime.now().strftime("%Y%m%d%H%M%S%f")

    @classmethod
    def __make_message(cls, message, target_user=None):
        message = {"message": message}
        message.update({"action_key": "{0}:{1}".format(cls.key(), cls._get_timestamp())})
        if target_user:
            message.update({"user": target_user})

        return message

    @classmethod
    def __store_log(cls, message):
        Datastore().store(message["action_key"], message)

    # overridable
    @classmethod
    def receive_feedback(cls, action_key, dict_data):
        if cls.is_my_key(action_key):
            Datastore().store(action_key, dict_data, nx=True)
        return {}

    @classmethod
    def is_my_key(cls, action_key):
        key_elements = action_key.split(":")
        if len(key_elements) > 0 and key_elements[0] == cls.key():
            return True
        else:
            return False


class RecognitionObserver(object):

    def __init__(self, schedule_func, send_func):
        # scheduler is a function(interval(delay), callback)
        self.schedule_func = schedule_func
        # sender is a function(message)
        self.send_func = send_func
        self.__recognizers = []
        self.__actions = []

    def set_recognizer(self, *recognizers):
        for r in recognizers:
            r.set_observer(self)
            self.__recognizers.append(r)

    def set_action(self, *actions):
        for a in actions:
            self.__set_action(a)

    def __set_action(self, action):
        is_included = True
        recognizer_names = [rc.key() for rc in self.__recognizers]

        for r in action.recognizers:
            if not r.key() in recognizer_names:
                is_included = False

        if is_included:
            self.__actions.append(action)
        else:
            raise Exception(action.key() + "'s recognizer is not registered yet")

    def get_recognizer(self, recognizer_class):
        result = None
        for r in self.__recognizers:
            if recognizer_class.key() == r.key():
                result = r

        return result

    def remove_recognizer(self, recognizer_class):
        key = recognizer_class.key()
        self.__recognizers[key].remove_observer()
        del self.__recognizers[key]

    def remove_action(self, action_class):
        del self.__actions[action_class.key()]

    def run(self):
        # run recognizing schedule jobs
        for r in self.__recognizers:
            if r.interval:
                self.schedule_func(r.interval, r.invoke)

    def notify(self, invoked_recognizer):
        # notify actions that data is recognized
        # todo have to think about each action's error handling (is Exception occures, next is not scheduled)
        for a in self.__actions:
            if a.has_recognizer(invoked_recognizer):
                message = a.trigger()
                if message:
                    self.send_func(message)

        # schedule for next recognition
        self.schedule_func(invoked_recognizer.interval, invoked_recognizer.invoke)

    def receive_feedback(self, action_key, feedback):
        # notify actions that data is recognized
        # todo think about action for feedback
        response = ""
        for a in self.__actions:
            if a.is_my_key(action_key):
                response = a.receive_feedback(action_key, feedback)

        self.send_func(response)
