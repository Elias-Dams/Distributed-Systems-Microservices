from flask import Flask
from flask import request as flask_request
from flask_restful import Resource, Api, reqparse
import requests
import psycopg2
import hashlib


app = Flask("users")
api = Api(app)

RETRIES = 3  # Number of times to retry the request

conn = None

while conn is None:
    try:
        conn = psycopg2.connect(dbname="users", user="postgres", password="postgres", host="users_persistence")
        print("DB connection succesful")
    except psycopg2.OperationalError:
        import time
        time.sleep(1)
        print("Retrying DB connection")

def add_activity(username, activity):
    global RETRIES
    for i in range(RETRIES):
        try:
            requests.post("http://activities:5000/activities/add", json={'username': username, 'activity': activity})
            break
        except requests.exceptions.RequestException:
            if i == RETRIES - 1:
                raise Exception(f"service is not reachable")
            print(f"connection to activities service failed.")
            continue

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

def add_friend(username_1, username_2):
    cur = conn.cursor()

    # Get the user IDs of the given usernames
    cur.execute('SELECT id FROM users WHERE username = %s OR username = %s', (username_1, username_2))
    user_ids = cur.fetchall()

    if len(user_ids) < 2:
        return False

    # Make sure user_id_1 is smaller than user_id_2
    user_id_1, user_id_2 = sorted(user_ids)

    cur.execute('SELECT 1 FROM friends WHERE user_id_1 = %s AND user_id_2 = %s', (user_id_1, user_id_2))
    exists = cur.fetchone() is not None

    if not exists:
        cur.execute('INSERT INTO friends (user_id_1, user_id_2) VALUES (%s, %s)', (user_id_1, user_id_2))
        conn.commit()

        # add the activity
        add_activity(username_1, f"Made a friend")
        return True
    return False

def get_friends(username, by_id=None):
    cur = conn.cursor()

    # Get the user ID corresponding to the given username
    cur.execute('SELECT id FROM users WHERE username = %s', (username,))
    user_id = cur.fetchone()

    if user_id is None:
        return False, []

    # Get the IDs of all friends of the user
    cur.execute('''
        SELECT user_id_2 FROM friends
        WHERE user_id_1 = %s
        UNION
        SELECT user_id_1 FROM friends
        WHERE user_id_2 = %s
    ''', (user_id[0], user_id[0]))
    friend_ids = [row[0] for row in cur.fetchall()]
    if len(friend_ids) == 0:
        return True, []

    if by_id and bool(by_id.lower() == 'true'):
        return True, friend_ids

    # Get the usernames of all friends
    cur.execute('SELECT username FROM users WHERE id IN %s', (tuple(friend_ids),))
    friends = [row[0] for row in cur.fetchall()]

    return True, friends

def get_userdata(username=None, user_id=None):
    cur = conn.cursor()
    if username:
        cur.execute("SELECT id, username, password FROM users WHERE username = %s;", (username,))
        result = cur.fetchone()
    elif user_id:
        cur.execute("SELECT id, username, password FROM users WHERE id = %s;", (user_id,))
        result = cur.fetchone()
    else:
        return False, None
    if result:
        return True, {'id': result[0], 'username': result[1], 'password': result[2]}
    return False, None

class UserExists(Resource):
    def get(self):
        args = flask_request.args
        if 'username' not in args and 'password' not in args:
            return {'message': 'Invalid request. Please provide both username and password.', 'success': False}, 400
        exists = user_exists(args['username'], args['password'])
        return {'success': exists}, 200 if exists else 404

class GetUserdata(Resource):
    def get(self):
        args = flask_request.args
        if 'username' not in args and 'user_id' not in args:
            return {'message': 'Invalid request. Please provide the username or user_id.', 'success': False}, 400
        if 'user_id' in args:
            status, user_data = get_userdata(user_id=args['user_id'])
        else:
            status, user_data = get_userdata(username=args['username'])
        return {'success': status, 'result': user_data}, 200 if status else 404

class AddUser(Resource):
    def post(self):
        request_data = flask_request.json
        username = request_data.get('username')
        password = request_data.get('password')
        if not username or not password:
            return {'message': 'Invalid request. Please provide both username and password.', 'success': False}, 400
        return {'success': add_user(username, password)}, 200

class FriendsOfUser(Resource):
    def get(self):
        args = flask_request.args
        if 'user' not in args:
            return {'message': 'Invalid request. Please provide a user.', 'success': False}, 400
        if 'by_id' in args:
            status, friends = get_friends(args['user'], args['by_id'])
        else:
            status, friends = get_friends(args['user'])
        return {'success': status, 'result': friends}, 200 if status else 404

class AddFriends(Resource):
    def post(self):
        request_data = flask_request.json
        user_1 = request_data.get('user_1')
        user_2 = request_data.get('user_2')
        if not user_2 or not user_1:
            return {'message': 'Invalid request. Please provide 2 users.', 'success': False}, 400
        return {'success': add_friend(user_1, user_2)}, 200

api.add_resource(UserExists, '/user/')
api.add_resource(GetUserdata, '/user/data')
api.add_resource(AddUser, '/user/add')
api.add_resource(FriendsOfUser, '/user/friends')
api.add_resource(AddFriends, '/user/add_friend')