import os
import csv
import itertools
import base64
import sayuri.rekognition as rekognition
from .sample_data import sample1, sample2


FILE_NAME = "training_data.csv"


class DataStruct():
    columns = ["pose>pitch", "pose>yaw", "emotion>sad", "smile", "eye_closed", "mouth_open_wide", "sex"]
    operations = ["min", "max", "avg"]

    @classmethod
    def make_header(cls):
        header = itertools.product(cls.columns, cls.operations)
        header = [" ".join(h) for h in header]
        return header

    @classmethod
    def write_file(cls, file_name, dataset):
        header = cls.make_header()
        with open(file_name, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file, lineterminator="\n")
            writer.writerow(header)
            for d in dataset:
                writer.writerow(d)

    @classmethod
    def append(cls, file_name, data):
        with open(file_name, 'a', newline='') as csv_file:
            writer = csv.writer(csv_file, lineterminator="\n")
            writer.writerow(data)


def create_data(recognized):
    row = []
    if "face_detection" in recognized:
        detecteds = recognized["face_detection"]
        detected = {}
        for c in DataStruct.columns:
            for d in detecteds:
                elements = c.split(">")
                value = d
                for e in elements:
                    if value and e in value:
                        value = value[e]
                    else:
                        value = None

                if c not in detected:
                    detected[c] = []
                if value is not None:
                    detected[c] += [value]

            if c in detected and len(detected[c]) > 0:
                for op in DataStruct.operations:
                    if op == "min":
                        row.append(min(detected[c]))
                    elif op == "max":
                        row.append(max(detected[c]))
                    elif op == "avg":
                        row.append(sum(detected[c])/len(detected))
            else:
                row += [0, 0, 0]

    return row


def append_image(path_to_image):
    if not os.path.isfile(path_to_image):
        raise Exception("image file does not exist.")

    with open(path_to_image, "rb") as img_byte:
        image = base64.b64encode(img_byte.read())

    from sayuri.env import Environment
    key = Environment().face_api_keys()
    client = rekognition.Client(key.key, key.secret, key.namespace, key.user_id)
    recognized = client.face_recognize(image, gender=True, emotion=True, mouth_open_wide=True, eye_closed=True)

    line = create_data(recognized)
    DataStruct.append(FILE_NAME, line)


def images_to_data():
    # load image
    path = os.path.join(os.path.dirname(__file__), "images")
    if not os.path.isdir(path):
        raise Exception("images directory does not exist.")

    image_files = list(sorted(filter(lambda f: f.upper().find(".PNG") > -1, os.listdir(path))))
    image_data = []
    for img_f in image_files:
        with open("/".join([path, img_f]), "rb") as img_byte:
            image_data.append(base64.b64encode(img_byte.read()))

    # post recognized image
    recognizeds = []
    from sayuri.env import Environment
    key = Environment().face_api_keys()
    client = rekognition.Client(key.key, key.secret, key.namespace, key.user_id)

    counter = 1
    for img_d in image_data:
        if counter % 10 == 0:
            print("now {0} files end...".format(counter))
        recognizeds.append(client.face_recognize(img_d, gender=True, emotion=True, mouth_open_wide=True, eye_closed=True))
        counter += 1

    """
    recognizeds.append(sample1)
    recognizeds.append(sample2)
    """

    # flatten data
    dataset = []
    for r in recognizeds:
        dataset.append(create_data(r))

    # write file
    DataStruct.write_file(FILE_NAME, dataset)


if __name__ == '__main__':
    images_to_data()
