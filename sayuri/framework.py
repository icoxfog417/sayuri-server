from datetime import datetime
from sayuri.datastore import Datastore


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

        # recognize data
        self.value = self.recognize(message)

        # store value into database
        self.observer.datastore.store_to_list(self.key(), self.value)

        # notify to observer that data is updated
        self.observer.notify(self)

    # must override
    def recognize(self, message):
        # get and return recognized data
        raise Exception("You have to implements recognize method")


class Action(object):

    def __init__(self, *recognizers):
        self.recognizers = recognizers  # recognizer classes
        self.data_size = 1
        self.is_replace = False

    @classmethod
    def key(cls):
        return cls.__name__.lower()

    def has_recognizer(self, recognizer):
        result = False
        for r in self.recognizers:
            if type(recognizer) == r:
                result = True

        return result

    def trigger(self, observer):
        result = None
        data = {}
        keys = []
        data_sizes = []
        for r in self.recognizers:
            key = r.key()
            keys.append(key)
            value = observer.datastore.get_list(key, self.data_size - 1)
            data_sizes.append(len(value))
            data.update({key: value})

        if self.validate_data(data):
            result = self.execute(data, observer)

        if result:
            message = {"message": result, "timestamp": self._get_timestamp(), "action": self.key()}
            observer.datastore.store(self.key(), message)
            return message
        else:
            return None

    # overridable
    def validate_data(self, data):
        return True

    # must override
    def execute(self, data, observer):
        # execute some action. it returns message object for chat bot(user __make_message).
        raise Exception("You have to implements execute method")

    @classmethod
    def value_to_dict(cls, value):
        result = {}
        values = value.split(",")
        for v in values:
            kv = v.split(":")
            if len(kv) > 1:
                result.update({kv[0]: kv[1]})
        return result

    @classmethod
    def _get_timestamp(cls):
        return datetime.now().strftime("%Y%m%d%H%M%S%f")


class RecognitionObserver(object):

    def __init__(self, schedule_func, send_func):
        # scheduler is a function(interval(delay), callback)
        self.schedule_func = schedule_func
        # sender is a function(message)
        self.send_func = send_func
        self.__recognizers = []
        self.__actions = []
        self.datastore = Datastore()
        self.is_continue = True

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

    def get_action(self, action_class):
        result = None
        for a in self.__actions:
            if action_class.key() == a.key():
                result = a

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

    def stop(self):
        # run recognizing schedule jobs
        self.is_continue = False

    def notify(self, invoked_recognizer):
        # notify actions that data is recognized
        # todo have to think about each action's error handling (if Exception occurred, next is not scheduled)
        for a in self.__actions:
            if a.has_recognizer(invoked_recognizer):
                message = a.trigger(self)
                if message:
                    self.send_func(message)

        # schedule for next recognition
        if self.is_continue and invoked_recognizer.interval:
            self.schedule_func(invoked_recognizer.interval, invoked_recognizer.invoke)
