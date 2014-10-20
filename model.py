from datetime import datetime, timedelta
import json
from datastore import Datastore


class Conference(object):
    KEY = "conference"

    def __init__(self):
        pass

    @classmethod
    def store(cls, conference):
        conference_key = conference["key"]
        value = json.dumps(conference)
        db = Datastore()
        db.store(conference_key, value)

    @classmethod
    def store_to_user(cls, user, conference):
        cls.store(conference)
        db = Datastore(user)
        db.store_to_list(cls.KEY, conference["key"])

    @classmethod
    def get(cls, conference_key):
        conference = Datastore().get(conference_key)
        if conference:
            return json.loads(conference)
        else:
            return None

    @classmethod
    def get_users_conference(cls, user, index=0):
        db = Datastore(user)
        keys = db.get_list(cls.KEY, index)
        conferences = []
        for key in keys:
            conferences.append(cls.get(key))
        return conferences

    @classmethod
    def update_rate(cls, conference_key, rate):
        conference = cls.get(conference_key)
        if rate > conference["rate"]:
            conference["rate"] = rate
            cls.store(conference)

    @classmethod
    def to_dict(cls, key, title, minutes):
        conference = {"key": key, "title": title,
                      "start": cls.to_str(datetime.now()), "minutes": minutes, "rate": -1}
        return conference

    @classmethod
    def to_str(cls, value):
        return value.strftime("%Y%m%d%H%M%S%f")

    @classmethod
    def to_datetime(cls, value):
        return datetime.strptime(value, "%Y%m%d%H%M%S%f")

    @classmethod
    def calculate_passed(cls, conference):
        if conference:
            passed = datetime.now() - cls.to_datetime(conference["start"])
            return passed.total_seconds() / 60
        else:
            return 0

    @classmethod
    def calculate_remained(cls, conference):
        if conference:
            limit = float(conference["minutes"])
            delta = datetime.now() - cls.to_datetime(conference["start"])
            return limit - (delta.total_seconds() / 60)
        else:
            return 0

    @classmethod
    def is_end(cls, conference):
        if cls.calculate_remained(conference) <= 0:
            return True
        else:
            return False

