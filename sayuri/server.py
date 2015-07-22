# -*- coding: utf-8 -*-
import os
import uuid
import logging
import tornado.httpclient
import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.auth
import tornado.httpserver
import tornado.websocket
import tornado.template
from sayuri.module import model as mdl
from sayuri.module import recognizers
from sayuri.module import actions


from tornado.options import define
define("port", default=80, help="run on the given port", type=int)


class Application(tornado.web.Application):
    observers = {}

    def __init__(self):
        from sayuri.env import Environment
        secret_key = Environment().secret_key()

        handlers = [
            (r"/", IndexHandler),
            (r"/home", HomeHandler),
            (r"/auth/login", LoginHandler),
            (r"/auth/logout", LogoutHandler),
            (r"/conference", ConferenceHandler),
            (r"/conference/image", ImageHandler),
            (r"/sayurisocket", ClientSocketHandler),
        ]
        settings = dict(
            login_url="/auth/login",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            cookie_secret=secret_key,
            debug=True,
        )

        # load and store prediction model
        machine_path = os.path.join(os.path.dirname(__file__), "static/machine")
        actions.FaceAction.store_machine(machine_path)
        tornado.web.Application.__init__(self, handlers, **settings)

    @classmethod
    def add_conference(cls, user, conference_key):
        if conference_key not in cls.observers:
            key = MessageManager.make_client_key(user, conference_key)
            instance = tornado.ioloop.IOLoop.instance()
            messenger = MessageManager(user, conference_key)
            cls.observers[key] = recognizers.SayuriRecognitionObserver(
                instance.add_timeout, messenger.send, user, conference_key)
            cls.observers[key].set_recognizer(recognizers.TimeRecognizer(),
                                              recognizers.FaceDetectIntervalRecognizer(),
                                              recognizers.FaceRecognizer())
            cls.observers[key].set_action(actions.TimeManagementAction(),
                                          actions.FaceDetectAction(),
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
        return tornado.escape.to_unicode(self.get_secure_cookie(mdl.Conference.KEY))

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
        self.set_secure_cookie("user", "Guest")
        self.redirect("/")


class LogoutHandler(BaseHandler):
    def get(self):
        Application.remove_conference(self.get_current_key())
        self.clear_cookie("user")
        self.clear_cookie(mdl.Conference.KEY)
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
            # show only conference of now
            # cs = Conference.get_users_conference(user, 0)
            pass

        if conference_key:
            conference = mdl.Conference.get(conference_key)
            cs.append(conference)
            if mdl.Conference.is_end(conference):
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

        if title and minutes and minutes.isdigit():
            key = str(uuid.uuid1())
            conference = mdl.Conference.to_dict(key, title, minutes)
            mdl.Conference.store_to_user(user, conference)
            self.set_secure_cookie(mdl.Conference.KEY, key)
            Application.add_conference(user, key)
            self.write({"conference": key})
        else:
            self.write({"conference": "", "message": "conference name or minutes is not set."})

    @tornado.web.authenticated
    def delete(self):
        Application.remove_conference(self.get_current_key())
        self.clear_cookie(mdl.Conference.KEY)
        self.write({})


class ImageHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        image_data = self.get_arguments("images[]")
        observer = Application.get_conference_observer(self.get_current_key())

        if image_data and observer:
            face = observer.get_recognizer(recognizers.FaceRecognizer)
            images = []
            for m in image_data:
                image = m.split(",")
                base64_image = image[len(image) - 1]
                images.append(base64_image)

            face.invoke(images)

        self.write({})


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
        conference = tornado.escape.to_unicode(self.get_secure_cookie(mdl.Conference.KEY))
        return MessageManager.make_client_key(user, conference)


def run(port=8443, ssl_key="", ssl_secret=""):
    io = tornado.ioloop.IOLoop.instance()
    application = Application()
    if ssl_key and ssl_secret:
        http_server = tornado.httpserver.HTTPServer(application,
                                                    ssl_options={
                                                        "keyfile": ssl_key,
                                                        "certfile": ssl_secret
                                                        })
    else:
        http_server = tornado.httpserver.HTTPServer(application)

    _port = int(os.environ.get("PORT", port))
    http_server.listen(_port)
    io.start()
