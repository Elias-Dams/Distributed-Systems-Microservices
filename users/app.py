from flask import Flask
from flask import request as flask_request
from flask_restful import Resource, Api, reqparse
import psycopg2
import hashlib


app = Flask("users")
api = Api(app)

conn = None

while conn is None:
    try:
        conn = psycopg2.connect(dbname="users", user="postgres", password="postgres", host="users_persistence")
        print("DB connection succesful")
    except psycopg2.OperationalError:
        import time
        time.sleep(1)
        print("Retrying DB connection")

def add_user(username, password):
    if not user_exists(username, password):
        cur = conn.cursor()
        # Hash the password using SHA256
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s);", (username, hashed_password))
        conn.commit()
        return True
    return False

def user_exists(username, password):
    cur = conn.cursor()
    # Hash the password using SHA256
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    cur.execute("SELECT COUNT(*) FROM users WHERE username = %s AND password = %s;", (username, hashed_password))
    return bool(cur.fetchone()[0]) # Either True or False


class UserExists(Resource):
    def post(self):
        request_data = flask_request.json
        username = request_data.get('username')
        password = request_data.get('password')
        if not username or not password:
            return {'message': 'Invalid request. Please provide both username and password.', 'success': False}, 400
        exists = user_exists(username, password)
        return {'success': exists}, 200

class AddUser(Resource):
    def put(self):
        args = flask_request.args
        if 'username' not in args or 'password' not in args:
            return {'message': 'Invalid request. Please provide both username and password.', 'success': False}, 400
        return {'success': add_user(args['username'], args['password'])}, 200

class FriendsOfUser(Resource):
    def get(self):
        pass

class AddFriends(Resource):
    def put(self):
        pass

api.add_resource(UserExists, '/user/')
api.add_resource(AddUser, '/user/add')
api.add_resource(FriendsOfUser, '/user/friends')
api.add_resource(AddFriends, '/user/add_friend')