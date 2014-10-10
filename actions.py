import json
from datastore import Datastore
from sayuri_model import Action
import recognizers


class GreetingAction(Action):
    def __init__(self):
        super().__init__(recognizers.TimeRecognizer)

    def execute(self, data):
        timezone = data[recognizers.TimeRecognizer.key()]
        # pre_value = Datastore().get_from_list(self.key())
        pre_value = ""
        pre_params = self.__split_value(pre_value)
        message = ""

        if len(pre_params) == 0 or (len(pre_params) > 0 and timezone != pre_params["timezone"]):
            if timezone == "morning":
                message = "Good morning"
            elif timezone == "daytime":
                message = "Good afternoon"
            elif timezone == "night":
                message = "Good night"

        if message:
            Datastore().store_to_list(self.key(), "{0}:{1}".format(timezone, self._get_timestamp()))
            return message
        else:
            return None

    @classmethod
    def __split_value(cls, value):
        values = value.split(":")
        if len(values) > 1:
            return {"timezone": values[0], "timestamp": values[1]}
        else:
            return {}

    @classmethod
    def receive_feedback(cls, action_key, dict_data):
        super().receive_feedback(action_key, dict_data)
        return receive_face_feedback(dict_data)


class MessageAction(Action):
    def __init__(self):
        super().__init__(recognizers.MessageRecognizer)

    def execute(self, data):
        return "Thank you for message"

    @classmethod
    def receive_feedback(cls, action_key, dict_data):
        super().receive_feedback(action_key, dict_data)
        return receive_face_feedback(dict_data)


def receive_face_feedback(face_feedback):
    response = {}

    def value_to_dict(value):
        result = {}
        values = value.split(",")
        for v in values:
            kv = v.split(":")
            if len(kv) > 1:
                result.update({kv[0]: kv[1]})
        return result

    # check feedback
    is_detected = True
    if not face_feedback:
        is_detected = False
    elif len(face_feedback.face_detection) == 0:
        is_detected = False

    # analyze feedback
    if is_detected:
        recognized = face_feedback.face_detection[0]
        who = value_to_dict(recognized.name)
        emotion = recognized.emotion.fields()

        if len(who) > 1 and len(emotion) > 1:
            who_top = max(who, key=who.get)
            emotion_top = max(emotion,  key=emotion.get)

            #if emotion[emotion_top] >= 0.7:
            if emotion[emotion_top] >= 0.1:
                response = {"message": "{0} send {1} feedback.".format(who_top, emotion_top)}

    return response
