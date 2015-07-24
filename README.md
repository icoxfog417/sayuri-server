[sayuri-server](https://sayuri-server.herokuapp.com/home)
=============

Sayuri judges the value of your conference.

## Architecture

* Using web camera to take your conference scene
* When getting the scene, Sayuri evaluates good or bad. Face detection is executed by [Rekognition API](https://rekognition.com/), and judges by `scikit-learn` SVM model.
* Evaluated data is stored in Redis.

run on Python tornado

## Run on your Heroku

Create your Rekognition account. Then deply by Heroku Button. 

[![Deploy](https://www.herokucdn.com/deploy/button.png)](https://heroku.com/deploy?template=https://github.com/icoxfog417/sayuri-server)

## Run on your Local

You have to create Rekognition account too. And then create `envs.json` at the root like below.


```
{
  "SECRET_KEY": "__YOUR_SECRET_KEY__",
  "REDIS_URL": "your redis url",
  "FACE_API_KEY": "your_key",
  "FACE_API_SECRET": "your_secret_key",
  "FACE_API_NAMESPACE": "namespace",
  "FACE_API_USER_ID": "user_id"
}
```
And You have to create a certificate to use SSL. Because Sayuri use `wss` protocol for security issue.

Create `ssl` folder at the root and make `serverkey.pem` and `servercrt.pem`.

For example ...

```
openssl genrsa -out serverkey.pem 2048
openssl req -new -key serverkey.pem -out server.csr
openssl x509 -req -in server.csr -signkey serverkey.pem -out servercrt.pem
```
