from flask import Flask
from flask import request as flask_request
from flask_restful import Resource, Api, reqparse
import requests
import psycopg2
import datetime
import pytz

app = Flask("activities")
api = Api(app)

conn = None

while conn is None:
    try:
        conn = psycopg2.connect(dbname="activities", user="postgres", password="postgres", host="activities_persistence")
        print("DB connection succesful")
    except psycopg2.OperationalError:
        import time
        time.sleep(1)
        print("Retrying DB connection")


def get_username(user_id):
    response = requests.get("http://users:5000/user/data", params={'user_id': user_id})

    if response.status_code == 200 and response.json()['success']:
        return response.json()['result']['username']
    else:
        return None

def get_user_id(username):
    response = requests.get("http://users:5000/user/data", params={'username': username})
    if response.status_code == 200 and response.json()['success']:
        return response.json()['result']['id']
    else:
        return None

def get_friend_ids(username):
    response = requests.get("http://users:5000/user/friends", params={'user': username, 'by_id': True})

    friend_list = []
    if response.status_code == 200 and response.json()['success']:
        friend_list = response.json()['result']

    return friend_list

def get_activities(username, num_entries):
    cur = conn.cursor()

    # get the user id's of the friends
    friend_list = get_friend_ids(username)
    if len(friend_list) == 0:
        return True, []


    # Create a string of comma-separated user IDs for the query
    user_ids_str = ','.join(str(uid) for uid in friend_list)

    cur.execute(f"SELECT timestamp, user_id, activity_type FROM activities WHERE user_id IN ({user_ids_str}) ORDER BY timestamp ASC LIMIT {num_entries}")

    result = []
    username_cache = {}
    timezone_local = pytz.timezone('Europe/Amsterdam')
    for row in cur.fetchall():
        user_id = row[1]
        if user_id not in username_cache:
            username_cache[user_id] = get_username(user_id)
        timestamp_local = row[0].astimezone(timezone_local)
        result.append((timestamp_local.strftime('%a %d %b (%Y) %H:%M'), username_cache[user_id], row[2]))

    return True, result

def add_activity(username, activity_type):
    cur = conn.cursor()

    user_id = get_user_id(username)
    if not user_id:
        return False

    timestamp = datetime.datetime.now()
    cur.execute("INSERT INTO activities (user_id, activity_type, timestamp) VALUES (%s, %s, %s);",
                (user_id, activity_type, timestamp))
    conn.commit()
    return True

class GetActivities(Resource):
    def get(self):
        args = flask_request.args
        if 'username' not in args or 'amount' not in args:
            return {'message': 'Invalid request. Please provide the username and the amount of data.', 'success': False}, 400
        status, activity_data = get_activities(args['username'], args['amount'])
        return {'success': status, 'result': activity_data}, 200

class AddActivities(Resource):
    def post(self):
        request_data = flask_request.json
        username = request_data.get('username')
        activity = request_data.get('activity')
        if not username or not activity:
            return {'message': 'Invalid request. Please provide both user id and activity.', 'success': False}, 400
        return {'success': add_activity(username, activity)}, 200

api.add_resource(GetActivities, '/activities/')
api.add_resource(AddActivities, '/activities/add')