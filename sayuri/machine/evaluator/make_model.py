# coding: utf-8
import os
import numpy as np
from sklearn import preprocessing
from sklearn.cross_validation import train_test_split
from sklearn.grid_search import GridSearchCV
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline
from sklearn.externals import joblib
from sklearn import svm
import matplotlib.pyplot as plt
from sayuri.machine import MachineLoader

MODEL_FILE = os.path.join(os.path.dirname(__file__), MachineLoader.MACHINE_FILE)


def load_data(skip_header=1):
    import os
    data_file = os.path.join(os.path.dirname(__file__), "training_data_with_label.csv")
    header = []
    with open(data_file, newline=os.linesep) as f:
        header = next(f).replace(os.linesep, "").split(",")
    dataset = np.genfromtxt(data_file, delimiter=",", skip_header=skip_header)
    y = dataset[:, 0]  # left side data is label
    X = dataset[:, range(1, dataset.shape[1])]

    return {"dataset": dataset, "header": header, "y": y, "X": X}


def make_model(y, X, columns, save_model=False):
    # select feature
    _X = X[:, columns]

    # reguralization
    scaler = preprocessing.StandardScaler()
    _X = scaler.fit_transform(_X)

    x_train, x_test, y_train, y_test = train_test_split(_X, y, test_size=0.25, random_state=42)

    candidates = [{'kernel': ["rbf"], 'gamma': [1e-3, 1e-4], 'C': [1, 10, 100]},
                  {'kernel': ['linear'], 'C': [1, 10, 100]}]

    clf = GridSearchCV(svm.SVC(C=1), candidates, cv=5, scoring="f1")
    clf.fit(x_train, y_train)

    for params, mean_score, scores in sorted(clf.grid_scores_, key=lambda s: s[1], reverse=True):
        print("%0.3f (+/-%0.03f) for %r" % (mean_score, scores.std() / 2, params))

    model = clf.best_estimator_
    y_predict = model.predict(x_test)

    print(classification_report(y_test, y_predict, target_names=["good", "bad"]))

    # plot boundary
    x_min, x_max = x_test[:, 0].min() - 1, x_test[:, 0].max() + 1
    y_min, y_max = x_test[:, 1].min() - 1, x_test[:, 1].max() + 1
    h = .02  # step size
    xx, yy = np.meshgrid(np.arange(x_min, x_max, h), np.arange(y_min, y_max, h))
    z = model.predict(np.c_[xx.ravel(), yy.ravel()])
    mean = {}
    mean["0"] = [np.average(xx.ravel()[z == 0]), np.average(yy.ravel()[z == 0])]
    mean["1"] = [np.average(xx.ravel()[z == 1]), np.average(yy.ravel()[z == 1])]
    z = z.reshape(xx.shape)
    plt.contourf(xx, yy, z, cmap=plt.cm.Paired)
    plt.axis('off')

    # plot test result (2d)
    plt.scatter(x_test[y_test == y_predict, 0], x_test[y_test == y_predict, 1], color="blue", cmap=plt.cm.Paired)
    plt.scatter(x_test[y_test != y_predict, 0], x_test[y_test != y_predict, 1], color="red", cmap=plt.cm.Paired)
    plt.scatter(mean["0"][0], mean["0"][1], color="green", cmap=plt.cm.Paired)
    plt.scatter(mean["1"][0], mean["1"][1], color="green", cmap=plt.cm.Paired)
    
    plt.show()

    if save_model:
        pipe = Pipeline([("scaling", scaler), ("estimator", model)])
        if sum(pipe.predict(scaler.inverse_transform(x_test)) != y_predict) > 0:
            raise Exception("Pipeline is not correct")
        joblib.dump(pipe, MODEL_FILE)
        return pipe

    return model
