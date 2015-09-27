from io import open
import random
import string
import json

from flask import Flask, render_template, request, redirect, url_for, flash, \
    jsonify
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from flask import session as login_session
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
from flask import make_response
import requests

from database_setup import User, base, Playlist, Song

app = Flask(__name__)

GOOGLE_CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "proj3"

# Connect to database
engine = create_engine('sqlite:///test.db')
base.metadata.bind = engine

db_session = sessionmaker(bind=engine)
session = db_session()


# Create anti-forgery state token
@app.route('/login')
def login():
    """ Encodes login URL for anti-forgery state token. """
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/fb_disconnect')
def fb_disconnect():
    """
    Revoke a current user's token and reset their login_session on Facebook.
    Only disconnect a connected user.

    :return: response.
    """
    facebook_id = login_session['facebook_id']
    # The access token must have me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % \
          (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/g-connect', methods=['POST'])
def google_connect():
    """ Connects and authorizes user against Google's Google+ API. """

    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != GOOGLE_CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'),
            200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = get_user_id(data["email"])
    if not user_id:
        user_id = create_user(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;' \
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


@app.route('/disconnect/')
def disconnect():
    """ Disconnects the user based on login_session['provider'] """
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            g_disconnect()
            del login_session['gplus_id']
            del login_session['credentials']

        if login_session['provider'] == 'facebook':
            fb_disconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('home'))
    else:
        flash("You were not logged out.")
        return redirect(url_for('home'))


@app.route('/fb-connect', methods=['GET', 'POST'])
def fb_connect():
    """ Connects and authorizes user against Facebook's API. """

    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('facebook_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('facebook_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=' \
          'fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=' \
          '%s' % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    # let's strip out the information before the equals sign in our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&' \
          'height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = get_user_id(login_session['email'])
    if not user_id:
        user_id = create_user(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;' \
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/g-disconnect')
def g_disconnect():
    """
    Revoke a current user's token and reset their login_session
    Only disconnect a connected user.

    :return: response.
    """

    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/')
@app.route('/user/')
@app.route('/users/')
def home():
    """
    Renders the home template and passes on a list of all users and their names
    :return: home.html template.
    """
    users = session.query(User).order_by(asc(User.name)).all()
    return render_template('home.html', users=users)


@app.route('/user/<int:user_id>/', methods=['GET'])
def show_user(user_id):
    """
    Information about the user.
    :param user_id: ID of the user.
    :return: show-user.html template for user with ID <user_id>.
    """
    users = session.query(User).filter_by(id=user_id).all()
    playlist = session.query(Playlist).filter_by(user_id=user_id).all()
    return render_template('show-user.html',
                           user_id=user_id,
                           users=users,
                           playlists=playlist,
                           login_session=login_session)


def get_user_id(email):
    """
    Gets the users ID based on email addresss.
    :param email: the email address of the user to get ID for.
    :return: None.
    """
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return


def get_user_info(user_id):
    """
    Gets information about the user.
    :param user_id: the ID of the user.
    :return: user.
    """
    user = session.query(User).filter_by(id=user_id).one()
    return user


def create_user(the_login_session):
    """
    Creates a user from the the_login_session's parameters.
    :param the_login_session: current session.
    :return: users ID.
    """
    new_user = User(name=the_login_session['username'],
                    email=the_login_session['email'],
                    picture=the_login_session['picture'])
    session.add(new_user)
    session.commit()
    user = session.query(User).filter_by(
        email=the_login_session['email']).one()
    return user.id


# TODO: If the user isn't signed in, the local permission system is not active
@app.route('/user/<int:user_id>/playlist/create/', methods=['GET', 'POST'])
def create_playlist(user_id):
    """
    Creates a playlist.

    :param user_id: the ID of the user.
    :return: redirects to created playlist.
    """
    user = session.query(User).filter_by(id=user_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if user.id != login_session['user_id']:
        return "<script> function myFunction() {alert('You are not " \
               "authorized to edit this user.')};" \
               " </script><body onload='myFunction()''>"
    if request.method == 'POST':
        new_playlist = Playlist(name=request.form['name'],
                                description=request.form['description'],
                                user_id=login_session['user_id'])
        session.add(new_playlist)
        session.commit()
        return redirect(url_for('show_playlist', playlist_id=new_playlist.id))
    else:
        return render_template('create-playlist.html')


@app.route('/playlist/<int:playlist_id>/', methods=['GET'])
def show_playlist(playlist_id):
    """
    Shows the playlist with the ID <playlist_id>.
    :param playlist_id: ID of the user.
    :return: show-playlist.html.
    """
    playlist = session.query(Playlist).filter_by(id=playlist_id).one()
    creator = get_user_info(playlist.user_id)
    songs = session.query(Song).filter_by(playlist_id=playlist_id)
    return render_template('show-playlist.html',
                           playlist_id=playlist_id,
                           playlist=playlist,
                           creator=creator,
                           songs=songs,
                           login_session=login_session)


@app.route('/playlist/<int:playlist_id>/json')
def show_playlist_json(playlist_id):
    """
    JSON API to view information about the playlist.
    :param playlist_id: the ID of the playlist.
    :return:
    """
    playlist = session.query(Playlist).filter_by(id=playlist_id).one()
    songs = session.query(Song).filter_by(playlist_id=playlist_id).all()
    return jsonify(playlist=playlist.serialize,
                   songs=[s.serialize for s in songs])


# TODO: Delete songs before deleting playlist
@app.route('/playlist/<int:playlist_id>/delete/', methods=['GET', 'POST'])
def delete_playlist(playlist_id):
    """
    Deletes a playlist with ID <user_id>.
    :param playlist_id: ID of the playlist being deleted.
    :return: show_user.
    """
    playlist_to_delete = session.query(Playlist).filter_by(
        id=playlist_id).one()
    songs_to_delete = session.query(Song).filter_by(
        playlist_id=playlist_to_delete.id).all()
    if 'username' not in login_session:
        return redirect('/login')
    if login_session['user_id'] != playlist_to_delete.user_id:
        return "<script> function myFunction() {alert('You are not " \
               "authorized to edit this user.')};" \
               " </script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(playlist_to_delete)
        session.commit()
        flash("Playlist was deleted.")
        return redirect(url_for('show_user', user_id=playlist_to_delete.user_id))
    else:
        return render_template('delete-playlist.html',
                               playlist_to_delete=playlist_to_delete,
                               songs_to_delete=songs_to_delete)


@app.route('/playlist/<int:playlist_id>/edit/', methods=['GET', 'POST'])
def edit_playlist(playlist_id):
    """
    Edits playlist with ID <playlist_id>.
    :param playlist_id: ID of the playlist.
    :return: show_playlist.
    """
    playlist_to_edit = session.query(Playlist).filter_by(id=playlist_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if login_session['user_id'] != playlist_to_edit.user_id:
        return "<script> function myFunction() {alert('You are not " \
               "authorized to edit this user.')};" \
               " </script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            playlist_to_edit.name = request.form['name']
        if request.form['description']:
            playlist_to_edit.description = request.form['description']
        session.add(playlist_to_edit)
        session.commit()
        return redirect(url_for('show_playlist',
                                playlist_id=playlist_id))
    else:
        return render_template('edit-playlist.html',
                               playlist_id=playlist_id,
                               playlist_to_edit=playlist_to_edit)


@app.route('/user/<int:user_id>/edit/', methods=['GET', 'POST'])
def edit_user(user_id):
    """
    Edits info for user with ID <user_id>.
    :param user_id:  ID of the user.
    :return: show_user.
    """
    user_to_edit = session.query(User).filter_by(id=user_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if login_session['user_id'] != user_id:
        return "<script> function myFunction() {alert('You are not " \
               "authorized to edit this user.')};" \
               " </script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            user_to_edit.name = request.form['name']
        if request.form['email']:
            user_to_edit.email = request.form['email']
        session.add(user_to_edit)
        session.commit()
        flash('User {} updated successfully'.format(user_to_edit.name))
        return redirect(url_for('show_user', user_id=user_id))
    else:
        return render_template('edit-user.html',
                               user_id=user_id,
                               user_to_edit=user_to_edit)


@app.route('/playlist/<int:playlist_id>/song/<int:song_id>/', methods=['GET', 'POST'])
def show_song(song_id, playlist_id):
    """
    Shows song with ID <song_id>.
    :param playlist_id: the ID of the playlist.
    :param song_id: ID of the song.
    :return: show-song.html.
    """
    playlist = session.query(Playlist).filter_by(id=playlist_id).one()
    song = session.query(Song).filter_by(id=song_id).one()
    return render_template('show-song.html',
                           song_id=song,
                           playlist_id=playlist,
                           login_session=login_session)


@app.route('/playlist/<int:playlist_id>/song/<int:song_id>/json')
def show_song_json(playlist_id, song_id):
    """
    JSON API for information about the songs.
    :param playlist_id: the ID of the playlist.
    :param song_id: the ID of the playlist.
    :return:
    """
    song = session.query(Song).filter_by(id=song_id).one()
    return jsonify(song=song.serialize)


@app.route('/playlist/<int:playlist_id>/song/create/', methods=['GET', 'POST'])
def add_song_to_playlist(playlist_id):
    """
    Creates a song in the playlist with ID <playlist_id>.
    :param playlist_id: the ID of the playlist.
    :return: show_playlist.
    """
    playlist = session.query(Playlist).filter_by(id=playlist_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if login_session['user_id'] != playlist.user_id:
        return "<script> function myFunction() {alert('You are not " \
               "authorized to edit this user.')};" \
               " </script><body onload='myFunction()''>"
    if request.method == 'POST':
        song_to_add = Song(song_name=request.form['songname'],
                           artist=request.form['artistname'],
                           playlist_id=playlist_id,
                           user_id=playlist.user_id)
        session.add(song_to_add)
        session.commit()
        flash("{0} added to {1}".format(song_to_add.song_name, playlist.name))
        return redirect(url_for('show_playlist',
                                playlist_id=playlist_id))
    else:
        return render_template('add-song-to-playlist.html',
                               playlist_id=playlist_id)


@app.route('/playlist/<int:playlist_id>/song/<int:song_id>/edit/',
           methods=['GET', 'POST'])
def edit_song(song_id, playlist_id):
    """
    Edits song with the ID <song_id>.
    :param playlist_id: the ID of the playlist.
    :param song_id: the ID of the song.
    :return: show_song.
    """
    playlist = session.query(Playlist).filter_by(id=playlist_id).one()
    song_to_edit = session.query(Song).filter_by(id=song_id).one()
    playlists = session.query(Playlist).order_by(asc(Playlist.name))
    if 'username' not in login_session:
        return redirect('/login')
    if login_session['user_id'] != song_to_edit.user_id:
        return "<script> function myFunction() {alert('You are not " \
               "authorized to edit this user.')};" \
               " </script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            song_to_edit.song_name = request.form['name']
        if request.form['artist']:
            song_to_edit.artist = request.form['artist']
        session.add(song_to_edit)
        session.commit()
        return redirect(url_for('show_song', song_id=song_id))
    else:
        return render_template('edit-song.html', song_id=song_to_edit.id,
                               song_to_edit=song_to_edit,
                               playlist_id=playlist_id,
                               playlists=playlists)


@app.route('/playlist/song/<int:song_id>/delete/', methods=['GET', 'POST'])
def delete_song(song_id):
    """
    Deletes a song with ID <song_id>
    :param song_id: the ID of the song.
    :return: show_playlist.
    """
    song_to_delete = session.query(Song).filter_by(id=song_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if login_session['user_id'] != song_to_delete.user_id:
        return "<script> function myFunction() {alert('You are not " \
               "authorized to edit this user.')};" \
               " </script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(song_to_delete)
        session.commit()
        return redirect(url_for('show_playlist',
                                playlist_id=song_to_delete.playlist_id))
    else:
        return render_template('delete-song.html', song_id=song_id,
                               song_to_delete=song_to_delete)


def is_permitted(user_id):
    """
    If the user is not signed or has a mismatching ID for the functionality
    attempted to be accessed we display a popup with a warning.

    :param user_id: ID of the user.
    :return: JavaScript popup.
    """
    if 'username' not in login_session:
        return redirect('/login')
    if login_session['user_id'] != user_id:
        return "<script> function myFunction() {alert('You are not " \
               "authorized to edit this user.')};" \
               " </script><body onload='myFunction()''>"


if __name__ == '__main__':
    app.secret_key = 'secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
