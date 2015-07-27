import json
import base64
import pickle
from sayuri.datastore import Datastore
from sayuri.module import recognizers
from sayuri.module import model as mdl
from sayuri.framework import Action
from sayuri.machine import MachineLoader
from statistics import mean


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
    def store_machine(cls):
        import sayuri.machine.evaluator
        machine = MachineLoader.load(sayuri.machine.evaluator)
        Datastore().store(cls.key() + ":machine", cls.serialize(machine))

    @classmethod
    def load_machine(cls):
        machine = Datastore().get(cls.key() + ":machine")
        return cls.deserialize(machine)

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
            machine = self.load_machine()
            predictions = []
            params = []
            for d in detecteds:
                param = self.__get_parameters(d)
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
    def __get_parameters(cls, faces):
        if faces and len(faces["face_detection"]) > 0:
            pitches = []
            smiles = []
            for d in faces["face_detection"]:
                if "pose" in d and "pitch" in d["pose"]:
                    pitches.append(d["pose"]["pitch"])
                if "smile" in d:
                    smiles.append(d["smile"])

            pitch_min = 0
            smile_avg = 0
            if len(pitches) > 0:
                pitch_min = min(pitches)

            if len(smiles) > 0:
                smile_avg = mean(smiles)

            return pitch_min, smile_avg
        else:
            return None
