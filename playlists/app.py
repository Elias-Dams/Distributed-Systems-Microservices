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
    status = response.json()['success']
    if response.status_code == 200 and status:
        return response.json()['result']['id']
    else:
        return None
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

    # Return the ID of the new playlist
    return True, playlist_id

def get_playlists(username, shared=None):
    cur = conn.cursor()

    # Get the user's ID
    user_id = int(get_user_id(username))
    if not user_id:
        return False, None

    if shared is None:
        cur.execute('SELECT id, name FROM playlists WHERE user_id = %s', (user_id,))
    elif shared:
        cur.execute('SELECT id, name FROM playlists WHERE user_id = %s AND shared = TRUE', (user_id,))
    else:
        cur.execute('SELECT id, name FROM playlists WHERE user_id = %s AND shared = FALSE', (user_id,))

    return True, cur.fetchall()

class GetPlaylists(Resource):
    def get(self):
        args = flask_request.args
        if "shared" not in args:
            status, playlists = get_playlists(args['username'])
        else:
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
        pass

class AddPlaylistSong(Resource):
    def post(self):
        pass

class SharePlaylist(Resource):
    def post(self):
        pass

api.add_resource(GetPlaylists, '/playlists/')
api.add_resource(AddPlaylist, '/playlists/create')
api.add_resource(GetPlaylistSongs, '/playlists/songs')
api.add_resource(AddPlaylistSong, '/playlists/add_song')
api.add_resource(SharePlaylist, '/playlists/share')