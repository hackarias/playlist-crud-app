from flask import Flask, render_template, request, redirect, url_for, flash
from io import open
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import User, base, Playlist, Song
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

GOOGLE_CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "proj3"

# Connect to database
engine = create_engine('sqlite:///test.db')
base.metadata.bind = engine

db_session = sessionmaker(bind=engine)
session = db_session()


@app.route('/login')
def login():
    """ Encodes login URL for anti-forgery state token. """

    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def g_connect():
    """ Connects and authorizes user against Google's Google+ API. """

    # Validating state token
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
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={'
           '}'.format(access_token))
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
    user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(user_info_url, params=params)
    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    #
    user_id = get_user_id(login_session['email'])
    if not user_id:
        create_user(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;\
        -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as {}".format(login_session['username']))
    print "done!"
    return output


@app.route('/gdisconnect')
def g_disconnect():
    """
    Revoke a current user's token and reset their login_session
    Only disconnect a connected user.
    """

    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token={}'.format(
        access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    # Reset the user's session.
    if result['status'] == '200':
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/')
@app.route('/user/')
@app.route('/users/')
def home():
    """ Renders the home template and passes on a list of all users and their
     names
    """
    users = session.query(User).order_by(asc(User.name))
    return render_template('home.html', users=users)


@app.route('/user/<int:user_id>/')
def show_user(user_id):
    """
    Information about the user.
    :param user_id: ID of the user.
    :return:
    """
    users = session.query(User).filter_by(id=user_id)
    playlist = session.query(Playlist).filter_by(user_id=user_id)
    return render_template('show-user.html',
                           user_id=user_id,
                           users=users,
                           playlists=playlist)


def get_user_id(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return


def get_user_info(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def create_user(login_session):
    new_user = User(name=login_session['username'],
                    email=login_session['email'],
                    picture=login_session['picture'])
    session.add(new_user)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


@app.route('/playlist/create/', methods=['GET', 'POST'])
def create_playlist():
    """
    Creates a playlist for the user.

    :return: redirect to the users profile
    """
    if 'username' not in login_session:
        return redirect('/login')
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
    Stores all playlists for user <user_id>.
    :param playlist_id: ID of the user.
    """
    playlist = session.query(Playlist).filter_by(id=playlist_id).one()
    creator = session.query(User).filter_by(id=playlist.user_id).one()
    songs = session.query(Song).filter_by(user_id=playlist.user_id)
    return render_template('show-playlist.html',
                           playlist_id=playlist_id,
                           playlist=playlist,
                           creator=creator,
                           songs=songs)


@app.route('/playlist/<int:playlist_id>/delete/',
           methods=['GET', 'POST'])
def delete_playlist(playlist_id):
    """
    Deletes a playlist with ID <user_id>.
    :param playlist_id: ID of the playlist being deleted.
    :return:
    """
    playlist = session.query(Playlist).filter_by(id=playlist_id).one()
    playlist_to_delete = session.query(Playlist).filter_by(
        id=playlist_id).one()
    if request.method == 'POST':
        session.delete(playlist_to_delete)
        flash("Playlist was deleted.")
        session.commit()
        return redirect(url_for('show_user', user_id=login_session['user_id']))
    else:
        return render_template('delete-playlist.html',
                               playlist=playlist,
                               playlist_to_delete=playlist_to_delete)


@app.route('/playlist/<int:playlist_id>/edit/',
           methods=['GET', 'POST'])
def edit_playlist(playlist_id):
    playlist_to_edit = session.query(Playlist).filter_by(id=playlist_id).one()
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


# FIXME: Clicking delete button doesn't trigger a POST request to delete user
@app.route('/user/<int:user_id>/delete/', methods=['GET', 'POST'])
def delete_user(user_id):
    user_to_delete = session.query(User).filter_by(id=user_id).one()
    if 'username' not in login_session:
        return redirect('login')
    if login_session['user_id'] != user_id:
        return "<script> function myFunction() {alert('You are not " \
               "authorized to delete this user.')};" \
               " </script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(user_to_delete)
        session.commit()
        flash('User {} was deleted successfully'.format(user_to_delete.name))
        return redirect(url_for('home'))
    else:
        return render_template('delete-user.html', deleted=user_to_delete)


if __name__ == '__main__':
    app.secret_key = 'secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
