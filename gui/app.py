from flask import Flask, render_template, redirect, request, url_for
import requests

app = Flask(__name__)


# The Username & Password of the currently logged-in User
username = None
password = None

session_data = dict()


def save_to_session(key, value):
    session_data[key] = value


def load_from_session(key):
    return session_data.pop(key) if key in session_data else None  # Pop to ensure that it is only used once


@app.route("/")
def feed():
    # ================================
    # FEATURE 9 (feed)
    #
    # Get the feed of the last N activities of your friends.
    # ================================

    global username

    N = 10

    if username is not None:
        response = requests.get("http://activities:5000/activities", params={'username': username, 'amount': N})
        feed = [["oei", "oei", "oei"]]
        if response.status_code == 200 and response.json()['success']:
            feed = response.json()['result']
    else:
        feed = []

    return render_template('feed.html', username=username, password=password, feed=feed)


@app.route("/catalogue")
def catalogue():
    songs = requests.get("http://songs:5000/songs").json()

    return render_template('catalogue.html', username=username, password=password, songs=songs)


@app.route("/login")
def login_page():

    success = load_from_session('success')
    return render_template('login.html', username=username, password=password, success=success)


@app.route("/login", methods=['POST'])
def actual_login():
    req_username, req_password = request.form['username'], request.form['password']

    # ================================
    # FEATURE 2 (login)
    #
    # send the username and password to the microservice
    # microservice returns True if correct combination, False if otherwise.
    # Also pay attention to the status code returned by the microservice.
    # ================================

    response = requests.post("http://users:5000/user", json={'username': req_username, 'password': req_password})
    user_exists = response.json()['success']
    success = response.status_code == 200 and user_exists

    save_to_session('success', success)
    if success:
        global username, password

        username = req_username
        password = req_password

    return redirect('/login')


@app.route("/register")
def register_page():
    success = load_from_session('success')
    return render_template('register.html', username=username, password=password, success=success)


@app.route("/register", methods=['POST'])
def actual_register():

    req_username, req_password = request.form['username'], request.form['password']

    # ================================
    # FEATURE 1 (register)
    #
    # send the username and password to the microservice
    # microservice returns True if registration is succesful, False if otherwise.
    #
    # Registration is successful if a user with the same username doesn't exist yet.
    # ================================

    response = requests.put("http://users:5000/user/add", params={'username': req_username, 'password': req_password})
    user_exists = response.json()['success']
    success = response.status_code == 200 and user_exists
    save_to_session('success', success)

    if success:
        global username, password

        username = req_username
        password = req_password

    return redirect('/register')


@app.route("/friends")
def friends():
    success = load_from_session('success')

    global username

    # ================================
    # FEATURE 4
    #
    # Get a list of friends for the currently logged-in user
    # ================================

    if username is not None:
        response = requests.get("http://users:5000/user/friends", params={'user': username})
        friend_list = []
        if response.status_code == 200 and response.json()['success']:
            friend_list = response.json()['result']
    else:
        friend_list = []

    return render_template('friends.html', username=username, password=password, success=success, friend_list=friend_list)


@app.route("/add_friend", methods=['POST'])
def add_friend():

    # ==============================
    # FEATURE 3
    #
    # send the username of the current user and the username of the added friend to the microservice
    # microservice returns True if the friend request is successful (the friend exists & is not already friends), False if otherwise
    # ==============================

    global username
    req_username = request.form['username']

    response = requests.put("http://users:5000/user/add_friend", params={'user_1': username, 'user_2': req_username})
    friend_added = response.json()['success']
    success = response.status_code == 200 and friend_added
    save_to_session('success', success)

    return redirect('/friends')


@app.route('/playlists')
def playlists():
    global username

    my_playlists = []
    shared_with_me = []

    if username is not None:
        # ================================
        # FEATURE
        #
        # Get all playlists you created and all playlist that are shared with you. (list of id, title pairs)
        # ================================
        response = requests.get("http://playlists:5000/playlists", params={'username': username, 'shared': False})
        status = response.json()['success']
        if response.status_code == 200 and status:
            my_playlists = response.json()['result']

        response = requests.get("http://playlists:5000/playlists", params={'username': username, 'shared': True})
        status = response.json()['success']
        if response.status_code == 200 and status:
            shared_with_me = response.json()['result']

    return render_template('playlists.html', username=username, password=password, my_playlists=my_playlists, shared_with_me=shared_with_me)


@app.route('/create_playlist', methods=['POST'])
def create_playlist():
    # ================================
    # FEATURE 5
    #
    # Create a playlist by sending the owner and the title to the microservice.
    # ================================
    global username
    title = request.form['title']

    requests.post("http://playlists:5000/playlists/create", json={'username': username, 'title': title})

    return redirect('/playlists')


@app.route('/playlists/<int:playlist_id>')
def a_playlist(playlist_id):
    # ================================
    # FEATURE 7
    #
    # List all songs within a playlist
    # ================================
    songs = []

    response = requests.get("http://playlists:5000/playlists/songs", params={'playlist_id': playlist_id})
    status = response.json()['success']
    if response.status_code == 200 and status:
        songs = response.json()['result']

    return render_template('a_playlist.html', username=username, password=password, songs=songs, playlist_id=playlist_id)


@app.route('/add_song_to/<int:playlist_id>', methods=["POST"])
def add_song_to_playlist(playlist_id):
    # ================================
    # FEATURE 6
    #
    # Add a song (represented by a title & artist) to a playlist (represented by an id)
    # ================================
    global username

    title, artist = request.form['title'], request.form['artist']

    requests.post("http://playlists:5000/playlists/add_song",
                 json={'title': title, 'artist': artist, 'playlist_id': playlist_id, "user": username})

    return redirect(f'/playlists/{playlist_id}')


@app.route('/invite_user_to/<int:playlist_id>', methods=["POST"])
def invite_user_to_playlist(playlist_id):
    # ================================
    # FEATURE 8
    #
    # Share a playlist (represented by an id) with a user.
    # ================================
    global username

    recipient = request.form['user']

    requests.post("http://playlists:5000/playlists/share",
                  json={'user': username, 'recipient': recipient, 'playlist_id': playlist_id})

    return redirect(f'/playlists/{playlist_id}')


@app.route("/logout")
def logout():
    global username, password

    username = None
    password = None
    return redirect('/')
