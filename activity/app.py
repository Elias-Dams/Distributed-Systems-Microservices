from flask import Flask
from flask_restful import Api

app = Flask("activities")
api = Api(app)