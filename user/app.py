from flask import Flask
from flask_restful import Api

app = Flask("users")
api = Api(app)