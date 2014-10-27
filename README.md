sayuri-server
=============

Sayuri judges the value of your conference.

## Architecture
* Using web camera to take your conference scene
* When getting the scene, Sayuri evaluates good or bad. Face detection is done by [Rekognition API](https://rekognition.com/), and judges by `scikit-learn` SVM model.
* Data is stored to Redis.

run on Python tornado

## Run on your Heroku
Create `secret_settings.py` at root for your secret settings.

```
SECRET_KEY = "" # for your session key
REDIS_URL = "" # your redis url

# Rekognition API key
FACE_API_KEY = ""
FACE_API_SECRET = ""
FACE_API_NAMESPACE = ""
FACE_API_USER_ID = ""
```
Websocket protocol is `wss` (Because of security. Heroku seemes to support only `wss`.), So you have to prepare ssl certification.  
Create `ssl` folder and make `serverkey.pem` and `servercrt.pem`.

For example ...

```
openssl genrsa -out serverkey.pem 2048
openssl req -new -key serverkey.pem -out server.csr
openssl x509 -req -in server.csr -signkey serverkey.pem -out servercrt.pem
```

