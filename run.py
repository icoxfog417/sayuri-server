import os
from sayuri import server


if __name__ == "__main__":
    if os.path.isdir(os.path.join(os.path.dirname(__file__), "ssl")):
        ssl_key = os.path.join(os.path.dirname(__file__), "ssl/serverkey.pem")
        ssl_secret = os.path.join(os.path.dirname(__file__), "ssl/servercrt.pem")
        server.run(ssl_key, ssl_secret)
    else:
        server.run()
