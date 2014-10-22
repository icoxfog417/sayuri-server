# -*- coding: utf-8 -*-
import os
import uuid
import json
import logging
from datetime import datetime
import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.websocket
import tornado.template
import secret_settings
from datastore import Datastore
from recognizers import SayuriRecognitionObserver
from model import Conference
import recognizers
from actions import FaceAction
import actions


from tornado.options import define
define("port", default=80, help="run on the given port", type=int)


class Application(tornado.web.Application):
    observers = {}

    def __init__(self):
        handlers = [
            (r"/", IndexHandler),
            (r"/home", HomeHandler),
            (r"/login", LoginHandler),
            (r"/logout", LogoutHandler),
            (r"/conference", ConferenceHandler),
            (r"/conference/image", ImageHandler),
            (r"/sayurisocket", ClientSocketHandler),
        ]
        settings = dict(
            login_url="/login",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            cookie_secret=secret_settings.SECRET_KEY,
            debug=True,
        )

        # load and store prediction model
        model_path = os.path.join(os.path.dirname(__file__), "static/models/conf_predict.pkl")
        FaceAction.store_model(model_path)
        tornado.web.Application.__init__(self, handlers, **settings)

    @classmethod
    def add_conference(cls, user, conference_key):
        if conference_key not in cls.observers:
            key = MessageManager.make_client_key(user, conference_key)
            instance = tornado.ioloop.IOLoop.instance()
            messenger = MessageManager(user, conference_key)
            cls.observers[key] = SayuriRecognitionObserver(instance.add_timeout, messenger.send, user, conference_key)
            cls.observers[key].set_recognizer(recognizers.TimeRecognizer(),
                                              recognizers.FaceRecognizer())
            cls.observers[key].set_action(actions.TimeManagementAction(),
                                          actions.FaceAction())
            cls.observers[key].run()
            return True
        else:
            return False

    @classmethod
    def get_conference_observer(cls, key):
        if key in cls.observers:
            return cls.observers[key]
        else:
            return None

    @classmethod
    def remove_conference(cls, key):
        if key in cls.observers:
            cls.observers[key].stop()
            del cls.observers[key]
            return True
        else:
            return False


class MessageManager(object):

    def __init__(self, user, conference_key):
        self.client = self.make_client_key(user, conference_key)

    @classmethod
    def make_client_key(cls, user, conference_key):
        if user and conference_key:
            return user + ":" + conference_key
        else:
            return ""

    def send(self, message):
        if not message:
            return False
        else:
            ClientSocketHandler.broadcast(self.client, message)
            return True


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")

    def get_current_user_str(self):
        return tornado.escape.to_unicode(self.get_current_user())

    def get_current_conference_key(self):
        return tornado.escape.to_unicode(self.get_secure_cookie(Conference.KEY))

    def get_current_key(self):
        return MessageManager.make_client_key(self.get_current_user_str(), self.get_current_conference_key())


class HomeHandler(BaseHandler):
    def get(self):
        self.render("home.html")


class LoginHandler(BaseHandler):
    def get(self):
        self.redirect("/home")

    def post(self):
        #todo implements authorization
        self.set_secure_cookie("user", "demo_user")
        self.redirect("/")


class LogoutHandler(BaseHandler):
    def get(self):
        Application.remove_conference(self.get_current_key())
        self.clear_cookie("user")
        self.clear_cookie(Conference.KEY)
        self.redirect("/home")


class IndexHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("index.html")


class ConferenceHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):
        # return conference list of current use.
        user = self.get_current_user_str()
        conference_key = self.get_current_conference_key()
        key = self.get_current_key()
        cs = []
        conference = ""
        if user:
            cs = Conference.get_users_conference(user, 5)

        if conference_key:
            conference = Conference.get(conference_key)
            if Conference.is_end(conference):
                conference = ""
            elif not Application.get_conference_observer(key):
                Application.add_conference(user, conference_key)

        self.write({"conference": conference, "conferences": cs})

    @tornado.web.authenticated
    def post(self):
        # register conference and start observing client
        title = self.get_argument("title")
        minutes = self.get_argument("minutes")
        user = self.get_current_user_str()

        if self.get_current_conference_key():
            self.delete()

        if title and minutes:
            key = str(uuid.uuid1())
            conference = Conference.to_dict(key, title, minutes)
            Conference.store_to_user(user, conference)
            self.set_secure_cookie(Conference.KEY, key)
            Application.add_conference(user, key)
            self.write({"conference": key})
        else:
            self.write({"conference": "", "message": "conference name is not set."})

    @tornado.web.authenticated
    def delete(self):

        Application.remove_conference(self.get_current_key())
        self.clear_cookie(Conference.KEY)
        self.write({})


class ImageHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        image_data = self.get_argument("image")
        observer = Application.get_conference_observer(self.get_current_key())

        if image_data and observer:
            image_data = image_data.split(",")
            base64_image = image_data[len(image_data) - 1]
            face = observer.get_recognizer(recognizers.FaceRecognizer)
            face.invoke(base64_image)


class ClientSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = {}

    @classmethod
    def broadcast(cls, client, message):
        if client in cls.waiters:
            try:
                cls.waiters[client].write_message(message)
            except:
                logging.error("Error sending message", exc_info=True)

    def check_origin(self, origin):
        return True

    def open(self):
        if self.get_socket_group():
            ClientSocketHandler.waiters[self.get_socket_group()] = self

    def on_close(self):
        key = self.get_socket_group()
        if key and key in ClientSocketHandler.waiters:
            del ClientSocketHandler.waiters[key]

    def on_message(self, message):
        pass

    def get_socket_group(self):
        user = tornado.escape.to_unicode(self.get_secure_cookie("user"))
        conference = tornado.escape.to_unicode(self.get_secure_cookie(Conference.KEY))
        return MessageManager.make_client_key(user, conference)


def main():
    io = tornado.ioloop.IOLoop.instance()
    application = Application()
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(tornado.options.options.port)
    io.start()


if __name__ == "__main__":
    main()
