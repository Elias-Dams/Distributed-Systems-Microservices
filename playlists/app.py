from flask import Flask
from flask import request as flask_request
from flask_restful import Resource, Api, reqparse
import requests
import psycopg2
from psycopg2 import errorcodes


app = Flask("playlists")
api = Api(app)

RETRIES = 3  # Number of times to retry the request

conn = None

while conn is None:
    try:
        conn = psycopg2.connect(dbname="playlists", user="postgres", password="postgres", host="playlists_persistence")
        print("DB connection succesful")
    except psycopg2.OperationalError:
        import time
        time.sleep(1)
        print("Retrying DB connection")

def get_user_id(username):
    global RETRIES
    for i in range(RETRIES):
        try:
            response = requests.get("http://users:5000/user/data", params={'username': username})
            if response.status_code == 200 and response.json()['success']:
                return response.json()['result']['id']
            else:
                return None
        except requests.exceptions.RequestException:
            if i == RETRIES - 1:
                raise Exception(f"service is not reachable")
            print(f"connection to users service failed.")
            continue

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

def song_exits(title, artist):
    global RETRIES
    for i in range(RETRIES):
        try:
            response = requests.get("http://songs:5000/songs/exist", params={'title': title, 'artist': artist})
            if response.status_code != 200 or not response.json():
                return False
            return True
        except requests.exceptions.RequestException:
            if i == RETRIES - 1:
                raise Exception(f"service is not reachable")
            print(f"connection to songs service failed.")
            continue

def add_playlist(username, playlist_name):
    cur = conn.cursor()

    try:
        # Get the user's ID
        user_id = int(get_user_id(username))
        if not user_id:
            return False, None, 200
    except Exception as e:
        # the service could not be reached
        return False, [], 503

    # Add the playlist to the database
    cur.execute("INSERT INTO playlists (name, user_id) VALUES (%s, %s) RETURNING id;", (playlist_name, user_id))
    playlist_id = cur.fetchone()[0]

    # Commit the transaction and close the connection
    conn.commit()

    try:
        # add the activity
        add_activity(username, "created a playlist")
    except Exception as e:
        # the service could not be reached
        return False, [], 503

    # Return the ID of the new playlist
    return True, playlist_id, 200

def get_playlists(username, shared):
    cur = conn.cursor()

    try:
        # Get the user's ID
        user_id = int(get_user_id(username))
        if not user_id:
            return False, None, 200
    except Exception as e:
        # the service could not be reached
        return False, [], 503

    if not bool(shared.lower() == 'true'):
        cur.execute('SELECT id, name FROM playlists WHERE user_id = %s', (user_id,))
    else:
        cur.execute('SELECT playlists.id, playlists.name FROM playlists LEFT JOIN shared ON playlists.id = shared.playlist_id WHERE shared.user_id = %s', (user_id,))

    return True, cur.fetchall(), 200

def add_song_to_playlist(title, artist, playlist_id, username):
    cur = conn.cursor()

    try:
        # check if song exits
        if not song_exits(title, artist):
            return False, 200
    except Exception as e:
        # the service could not be reached
        return False, 503

    try:
        # Insert a new record into the playlist_songs table
        cur.execute("INSERT INTO playlist_songs (playlist_id, artist, title) VALUES (%s, %s, %s);",
                (int(playlist_id), artist, title))
        conn.commit()
    except psycopg2.IntegrityError as e:
        # Handle the unique constraint violation error
        if e.pgcode == errorcodes.UNIQUE_VIOLATION:
            conn.rollback()
            return False, 200
        conn.rollback()

    try:
        # add the activity
        add_activity(username, f"Added a song to a playlist")
    except Exception as e:
        # the service could not be reached
        return False, 503

    return True, 200

def get_playlist_songs(playlist_id):
    cur = conn.cursor()
    cur.execute("SELECT title, artist FROM playlist_songs WHERE playlist_id = %s", (int(playlist_id),))
    songs = cur.fetchall()
    if len(songs) == 0:
        return False, [], 200
    return True, songs, 200

def share_playlist(username, recipient, playlist_id):
    cur = conn.cursor()

    try:
        # Get the user's ID
        user_id = get_user_id(recipient)
        if not user_id:
            return False, 200
    except Exception as e:
        # the service could not be reached
        return False, 503

    try:
        # Add the playlist to the database
        cur.execute("INSERT INTO shared (playlist_id, user_id) VALUES (%s, %s);", (int(playlist_id), int(user_id)))
        conn.commit()
    except psycopg2.IntegrityError as e:
        # Handle the unique constraint violation error
        if e.pgcode == errorcodes.UNIQUE_VIOLATION:
            conn.rollback()
            return False, 200
        conn.rollback()

    try:
        # add the activity
        add_activity(username, f"Shared a playlist with a friend")
    except Exception as e:
        # the service could not be reached
        return False, 503

    return True, 200

class GetPlaylists(Resource):
    def get(self):
        args = flask_request.args
        if "shared" not in args:
            return {'message': 'Invalid request. Please provide shared.', 'success': False}, 400
        status, playlists, status_code = get_playlists(args['username'], args['shared'])
        return {'success': status, 'result': playlists}, status_code

class AddPlaylist(Resource):
    def post(self):
        request_data = flask_request.json
        username = request_data.get('username')
        title = request_data.get('title')
        if not username or not title:
            return {'message': 'Invalid request. Please provide both username and title.', 'success': False}, 400
        status, playlist_id, status_code = add_playlist(username, title)
        return {'success': status, "result": playlist_id}, status_code

class GetPlaylistSongs(Resource):
    def get(self):
        args = flask_request.args
        if "playlist_id" not in args:
            return {'message': 'Invalid request. Please provide a playlist id.', 'success': False}, 400
        status, songs, status_code = get_playlist_songs(args['playlist_id'])
        return {'success': status, 'result': songs}, status_code

class AddPlaylistSong(Resource):
    def post(self):
        request_data = flask_request.json
        title = request_data.get('title')
        artist = request_data.get('artist')
        playlist_id = request_data.get('playlist_id')
        user = request_data.get('user')
        if not artist or not title or not playlist_id or not user:
            return {'message': 'Invalid request. Please provide an artist, title, playlist_id and user.', 'success': False}, 400
        status, stats_code = add_song_to_playlist(title, artist, playlist_id, user)
        return {'success': status}, stats_code


class SharePlaylist(Resource):
    def post(self):
        request_data = flask_request.json
        user = request_data.get('user')
        recipient = request_data.get('recipient')
        playlist_id = request_data.get('playlist_id')
        if not user or not recipient or not playlist_id:
            return {'message': 'Invalid request. Please provide the user, recipient and playlist_id.',
                    'success': False}, 400
        status, stats_code = share_playlist(user, recipient , playlist_id)
        return {'success': status}, stats_code

api.add_resource(GetPlaylists, '/playlists/')
api.add_resource(AddPlaylist, '/playlists/create')
api.add_resource(GetPlaylistSongs, '/playlists/songs')
api.add_resource(AddPlaylistSong, '/playlists/add_song')
api.add_resource(SharePlaylist, '/playlists/share')