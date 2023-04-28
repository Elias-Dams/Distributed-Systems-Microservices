from flask import Flask
from flask_restful import Api

app = Flask("playlists")
api = Api(app)