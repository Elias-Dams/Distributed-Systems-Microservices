from flask import Flask
from flask import request as flask_request
from flask_restful import Resource, Api, reqparse
import psycopg2


app = Flask("activities")
api = Api(app)

conn = None

while conn is None:
    try:
        conn = psycopg2.connect(dbname="activities", user="postgres", password="postgres", host="activities_persistence")
        print("DB connection succesful activities")
    except psycopg2.OperationalError:
        import time
        time.sleep(1)
        print("Retrying DB connection")