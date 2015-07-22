import json
import base64
import pickle
from sklearn.externals import joblib
from sayuri.datastore import Datastore
from sayuri.module import recognizers
from sayuri.module import model as mdl
from sayuri.framework import Action


class TimeManagementAction(Action):
    def __init__(self):
        super().__init__(recognizers.TimeRecognizer)

    def execute(self, data, observer):
        comment = ""
        phase = data[recognizers.TimeRecognizer.key()][0]
        past_phase = observer.datastore.get_single(self.key() + ":phase")
        if phase != past_phase:
            observer.datastore.store_to_list(self.key() + ":phase", phase)
            if phase == recognizers.TimeRecognizer.PHASE_CLOSING:
                comment = "conference will close after 10 minutes. please wrap-up ."
            elif phase == recognizers.TimeRecognizer.PHASE_LIMIT:
                comment = "conference will close after 3 minutes."
            elif phase == recognizers.TimeRecognizer.PHASE_END:
                comment = "conference expired now. please exit quickly for next."

        return comment


class FaceDetectAction(Action):
    def __init__(self):
        super().__init__(recognizers.FaceDetectIntervalRecognizer)

    def execute(self, data, observer):
        return "begin detection"


class FaceAction(Action):
    def __init__(self):
        super().__init__(recognizers.FaceRecognizer)

    @classmethod
    def store_machine(cls, path):
        machine = joblib.load(path + "/conf_predict.pkl")
        summary = {}
        with open(path + "/data_summary.pkl", "rb") as fo:
            summary = pickle.load(fo)

        Datastore().store(cls.key() + ":machine", cls.serialize(machine))
        Datastore().store(cls.key() + ":summary", cls.serialize(summary))

    @classmethod
    def load_machine(cls):
        machine = Datastore().get(cls.key() + ":machine")
        summary = Datastore().get(cls.key() + ":summary")
        return cls.deserialize(machine), cls.deserialize(summary)

    @classmethod
    def serialize(cls, item):
        sd = pickle.dumps(item)
        sd = base64.b64encode(sd)
        return sd

    @classmethod
    def deserialize(cls, serialized):
        ds = base64.b64decode(serialized)
        ds = pickle.loads(ds)
        return ds

    def execute(self, data, observer):
        # check recognized image
        rate = ""
        advice = ""
        if recognizers.FaceRecognizer.key() in data:
            detecteds = json.loads(data[recognizers.FaceRecognizer.key()][0])
            machine, summary = self.load_machine()
            predictions = []
            params = []
            for d in detecteds:
                param = self.__get_parameters(d, summary)
                if param:
                    params.append(param)
                    predictions.append(machine.predict(param))

            if len(predictions) > 0:
                advice = self.__make_advice(params)
                rate = float(sum(predictions)) / len(predictions)
                mdl.Conference.update_rate(observer.conference_key, advice, rate)

        return json.dumps({"advice": advice, "rate": rate})


    @classmethod
    def __make_advice(cls, params):
        advice = ""
        if len(params) > 0:
            maxs = max(params)
            mins = min(params)
            advice = cls.__advice_cases(mins, -1,
                                        "everybody lose motivation... Do you really need this meeting?",
                                        "someone feel tired. Why don't you change the viewpoint of discussion?",
                                        "someone feel miserable. Let's change the mood.")

            praise = cls.__advice_cases(maxs, 1,
                                        "wonderful conference! excellent!",
                                        "everybody attending conference! very good.",
                                        "everybody relax and vivid! very good.")

            if praise:
                advice = praise

        return advice

    @classmethod
    def __advice_cases(cls, data, boundary, both, left, right):
        advice = ""
        if data[0] >= boundary and data[1] >= boundary:
            advice = both
        if data[0] >= boundary:
            advice = left
        if data[1] >= boundary:
            advice = right

        return advice

    @classmethod
    def __get_parameters(cls, faces, summary):
        if faces and len(faces["face_detection"]) > 0:
            pitches = []
            smiles = []
            for d in faces["face_detection"]:
                if "pose" in d and "pitch" in d["pose"]:
                    pitches.append(d["pose"]["pitch"])
                if "smile" in d:
                    smiles.append(d["smile"])

            min_pitches = 0
            max_smile = 0
            if len(pitches) > 0:
                min_pitches = min(pitches)
                min_pitches = cls.__regularization(min_pitches, summary, 0)

            if len(smiles) > 0:
                max_smile = max(smiles)
                max_smile = cls.__regularization(max_smile, summary, 1)

            return min_pitches, max_smile
        else:
            return None


    @classmethod
    def __regularization(cls, value, summary, index):
        data_size = float(summary["struct"]["len"])
        d_sum = summary["summary"][index]["sum"]
        d_max = summary["summary"][index]["max"]
        d_min = summary["summary"][index]["min"]
        d_sd = (d_max - d_min) / 4
        return (value - (d_sum / data_size)) / d_sd
