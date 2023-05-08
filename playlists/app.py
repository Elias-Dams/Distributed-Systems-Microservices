from flask import Flask
from flask import request as flask_request
from flask_restful import Resource, Api, reqparse
import requests
import psycopg2


app = Flask("playlists")
api = Api(app)

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
    response = requests.get("http://users:5000/user/data", params={'username': username})
    if response.status_code == 200 and response.json()['success']:
        return response.json()['result']['id']
    else:
        return None

def add_activity(username, activity):
    requests.post("http://activities:5000/activities/add", json={'username': username, 'activity': activity})

def add_playlist(username, playlist_name):
    cur = conn.cursor()

    # Get the user's ID
    user_id = int(get_user_id(username))
    if not user_id:
        return False, None

    # Add the playlist to the database
    cur.execute("INSERT INTO playlists (name, user_id) VALUES (%s, %s) RETURNING id;", (playlist_name, user_id))
    playlist_id = cur.fetchone()[0]

    # Commit the transaction and close the connection
    conn.commit()

    # add the activity
    add_activity(username, "created a playlist")

    # Return the ID of the new playlist
    return True, playlist_id

def get_playlists(username, shared):
    cur = conn.cursor()

    # Get the user's ID
    user_id = int(get_user_id(username))
    if not user_id:
        return False, None

    if not bool(shared.lower() == 'true'):
        cur.execute('SELECT id, name FROM playlists WHERE user_id = %s', (user_id,))
    else:
        cur.execute('SELECT playlists.id, playlists.name FROM playlists LEFT JOIN shared ON playlists.id = shared.playlist_id WHERE shared.user_id = %s', (user_id,))

    return True, cur.fetchall()

def add_song_to_playlist(title, artist, playlist_id, username):
    cur = conn.cursor()

    # check if song exits
    response = requests.get("http://songs:5000/songs/exist", params={'title': title, 'artist':artist})
    if not response.json():
        return False

    cur.execute("INSERT INTO playlist_songs (playlist_id, artist, title) VALUES (%s, %s, %s);",
                (int(playlist_id), artist, title))
    conn.commit()

    # add the activity
    add_activity(username, f"Added a song to a playlist")

    return True

def get_playlist_songs(playlist_id):
    cur = conn.cursor()
    cur.execute("SELECT title, artist FROM playlist_songs WHERE playlist_id = %s", (int(playlist_id),))
    songs = cur.fetchall()
    if len(songs) == 0:
        return False, []
    return True, songs

def share_playlist(username, recipient, playlist_id):
    cur = conn.cursor()

    # Get the user's ID
    user_id = get_user_id(recipient)
    if not user_id:
        return False

    # Add the playlist to the database
    cur.execute("INSERT INTO shared (playlist_id, user_id) VALUES (%s, %s);", (int(playlist_id), int(user_id)))

    # Commit the transaction and close the connection
    conn.commit()

    # add the activity
    add_activity(username, f"Shared a playlist with a friend")

    return True

class GetPlaylists(Resource):
    def get(self):
        args = flask_request.args
        if "shared" not in args:
            return {'message': 'Invalid request. Please provide shared.', 'success': False}, 400
        status, playlists = get_playlists(args['username'], args['shared'])
        return {'success': status, 'result': playlists}, 200

class AddPlaylist(Resource):
    def post(self):
        request_data = flask_request.json
        username = request_data.get('username')
        title = request_data.get('title')
        if not username or not title:
            return {'message': 'Invalid request. Please provide both username and title.', 'success': False}, 400
        status, playlist_id = add_playlist(username, title)
        return {'success': status, "result": playlist_id}, 200

class GetPlaylistSongs(Resource):
    def get(self):
        args = flask_request.args
        if "playlist_id" not in args:
            return {'message': 'Invalid request. Please provide a playlist id.', 'success': False}, 400
        status, songs = get_playlist_songs(args['playlist_id'])
        return {'success': status, 'result': songs}, 200

class AddPlaylistSong(Resource):
    def post(self):
        request_data = flask_request.json
        title = request_data.get('title')
        artist = request_data.get('artist')
        playlist_id = request_data.get('playlist_id')
        user = request_data.get('user')
        if not artist or not title or not playlist_id or not user:
            return {'message': 'Invalid request. Please provide an artist, title, playlist_id and user.', 'success': False}, 400
        return {'success': add_song_to_playlist(title, artist, playlist_id, user)}, 200


class SharePlaylist(Resource):
    def post(self):
        request_data = flask_request.json
        user = request_data.get('user')
        recipient = request_data.get('recipient')
        playlist_id = request_data.get('playlist_id')
        if not user or not recipient or not playlist_id:
            return {'message': 'Invalid request. Please provide the user, recipient and playlist_id.',
                    'success': False}, 400
        return {'success': share_playlist(user, recipient , playlist_id)}, 200

api.add_resource(GetPlaylists, '/playlists/')
api.add_resource(AddPlaylist, '/playlists/create')
api.add_resource(GetPlaylistSongs, '/playlists/songs')
api.add_resource(AddPlaylistSong, '/playlists/add_song')
api.add_resource(SharePlaylist, '/playlists/share')