import os
from sklearn.externals import joblib


class MachineLoader():
    MACHINE_FILE = "conf_predict.pkl"
    DATA_FILE = "data_summary.pkl"

    @classmethod
    def load(cls, pkg):
        machine = None
        summary = {}
        machine_file = cls.__get_pkg_path(pkg, cls.MACHINE_FILE)
        data_file = cls.__get_pkg_path(pkg, cls.DATA_FILE)

        if os.path.isfile(machine_file) and os.path.isfile(data_file):
            machine = joblib.load(machine_file)
            with open(data_file, "rb") as fo:
                import pickle
                summary = pickle.load(fo)
        else:
            raise Exception("{0} doesn't exist.".format(machine_file))

        return (machine, summary)

    @classmethod
    def __get_pkg_path(cls, pkg, file_name=""):
        pkg_path = os.path.dirname(pkg.__file__)
        if file_name:
            pkg_path = os.path.join(pkg_path, file_name)
        return pkg_path
