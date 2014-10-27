import json
import base64
import pickle
from sklearn.externals import joblib
from datastore import Datastore
import recognizers
from sayuri_framework import Action
from model import Conference


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
    def store_model(cls, path):
        model = joblib.load(path)
        serialized = pickle.dumps(model)
        serialized = base64.b64encode(serialized)
        Datastore().store(cls.key() + ":model", serialized)

    @classmethod
    def load_model(cls):
        serialized = Datastore().get(cls.key() + ":model")
        serialized = base64.b64decode(serialized)
        return pickle.loads(serialized)

    def execute(self, data, observer):
        # check recognized image
        response = ""
        if recognizers.FaceRecognizer.key() in data:
            detecteds = json.loads(data[recognizers.FaceRecognizer.key()][0])
            model = self.load_model()
            predictions = []
            for d in detecteds:
                param = self.get_parameters(d)
                if param:
                    predictions.append(model.predict(param))

            if len(predictions) > 0:
                good_rate = float(sum(predictions)) / len(predictions)
                response = "{0}".format(good_rate)
                Conference.update_rate(observer.conference_key, good_rate)

        return response

    def get_parameters(self, faces):
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

            if len(smiles) > 0:
                max_smile = max(smiles)

            return min_pitches, max_smile
        else:
            return None


