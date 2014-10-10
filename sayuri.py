# -*- coding: utf-8 -*-
import os
import uuid
import json
import logging
import urllib.request
import urllib.parse
import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.websocket
import secret_settings
import rekognition
from sayuri_model import RecognitionObserver
import recognizers
import actions


class Application(tornado.web.Application):
    observer = None

    def __init__(self, instance):
        handlers = [
            (r"/", HomeHandler),
            (r"/face", FaceHandler),
            (r"/bot/listen", BotHandler),
            (r"/sayurisocket", ClientSocketHandler),
        ]
        # todo have to think about xsrf
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            # xsrf_cookies=True,
            # cookie_secret=secret_settings.SECRET_KEY,
            debug=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

        Application.observer = RecognitionObserver(instance.add_timeout, send)
        Application.observer.set_recognizer(recognizers.TimeRecognizer(),
                                            recognizers.MessageRecognizer())
        Application.observer.set_action(actions.GreetingAction())


def face_recognize(face):
    if face:
        encoded = face.split(",")
        client = rekognition.Client(secret_settings.FACE_API_KEY,
                                    secret_settings.FACE_API_SECRET,
                                    secret_settings.FACE_API_NAMESPACE,
                                    secret_settings.FACE_API_USER_ID)

        obj = client.face_recognize(encoded[len(encoded) - 1], emotion=True, eye_closed=True)
        return obj
    else:
        return {"msg": "hugahuga"}


def send(message):

    if not message:
        return False

    # send to bot
    p = urllib.parse.urlencode(message)
    p = p.encode("utf-8")
    response = None
    # for local bot server. don't use proxy when local server.
    if secret_settings.BOT_HOME.find("http://localhost") > -1:
        proxy = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy)
        response = opener.open(secret_settings.BOT_HOME, p)
    else:
        request = urllib.request.Request(secret_settings.BOT_HOME, p)
        response = urllib.request.urlopen(request)

    content = response.read()
    content = json.loads(content.decode("utf-8"), object_hook=rekognition.AttributeDict)

    # see the client for feedback
    ClientSocketHandler.broadcast(message)

    return True


class HomeHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")


class FaceHandler(tornado.web.RequestHandler):
    def get(self):
        # url = "{0}://{1}{2}".format(self.request.protocol, self.request.host, self.request.uri)
        token = str(uuid.uuid1())
        self.set_secure_cookie("face_token", token)

    def post(self):
        # token = self.get_secure_cookie("face_token")
        face = self.get_argument("face")
        self.write(face_recognize(face))


class BotHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body.decode('utf-8'))
        handler = Application.observer.get_recognizer(recognizers.MessageRecognizer)

        if handler:
            handler.invoke(data)


class ClientSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()

    @classmethod
    def broadcast(cls, message):
        for waiter in cls.waiters:
            try:
                waiter.write_message(message)
            except:
                logging.error("Error sending message", exc_info=True)

    def check_origin(self, origin):
        return True

    def open(self):
        ClientSocketHandler.waiters.add(self)

    def on_close(self):
        ClientSocketHandler.waiters.remove(self)

    def on_message(self, message):
        # todo: separate feedback case and send data from client case
        parsed = tornado.escape.json_decode(message)
        face = face_recognize(parsed["face"])
        if "action_key" in parsed:
            action_key = parsed["action_key"]
            Application.observer.receive_feedback(action_key, face)


def main():
    io = tornado.ioloop.IOLoop.instance()
    application = Application(io)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(80)

    application.observer.run()
    io.start()


if __name__ == "__main__":
    main()
