from flask import Flask, request, url_for, render_template, flash, redirect, \
    flash, make_response
from flask import session as login_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import asc, create_engine
import random, string
from database_setup import base, Users
import json
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
import httplib2, requests

app = Flask(__name__)


# Connect to Database and create database session
engine = create_engine('sqlite:///test.db')
base.metadata.bind = engine

db_session = sessionmaker(bind=engine)
session = db_session()

GOOGLE_CLIENT_ID = json.loads(
    open('google_secrets.json', 'r').read())['web']['client_id']
GOOGLE_APP_ID = ''


@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state paramater'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data

    try:
        # Upgrade the auth code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check if the access token is valid.
    access_token = credentials.access_token
    url = 'https://www.googleapis.com/oauth2/v1/tokeninfo?' \
          'access_token={}'.format(access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there wawas an error in the access_token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access_token is used as intended
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("Token's user ID doesn't match "
                                            "given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the acces token is valid for this app.
    if result['issued_to'] != GOOGLE_CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID doesn't match app ID"), 401)
        print "Token's client ID doesn't match apps."
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check if user is already logget in.
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected'), 200)
        response.headers['Content-Type'] = 'application/json'

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo/"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']


@app.route('/login/')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html')


@app.route('/gdisconnect/')
def gdisconnect():
    # Disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Execute HTTP GET request to revoke current token.
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token={}'.format(
        access_token
    )
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == 200:
        # Reset the user's session.
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/')
@app.route('/users/')
def home():
    users = session.query(Users).order_by(asc(Users.name))
    return render_template('home.html', users=users)


@app.route('/user/<int:user_id>/')
def show_user(user_id):
    users = session.query(Users).filter_by(id=user_id)
    return render_template('show-user.html', user_id=user_id, users=users)


@app.route('/create/', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        user_to_create = Users(name=request.form['name'],
                               email=request.form['email'])
        session.add(user_to_create)
        session.commit()
        flash(
            'The user {} was successfully created'.format(user_to_create.name))
        return redirect(url_for('home'))
    else:
        return render_template('create-user.html')


@app.route('/user/<int:user_id>/edit/', methods=['GET', 'POST'])
def edit_user(user_id):
    user_to_edit = session.query(Users).filter_by(id=user_id).one()
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
        return render_template('edit-user.html', user_id=user_id,
                               user_to_edit=user_to_edit)


@app.route('/user/<int:user_id>/delete/', methods=['GET', 'POST'])
def delete_user(user_id):
    user_to_delete = session.query(Users).filter_by(id=user_id).one()
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
