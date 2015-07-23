from flask import Flask

app = Flask(__name__)


@app.route('/')
@app.route('/home/')
@app.route('/index/')
def home():
    return "This will be the home page"


@app.route('/login/')
def login():
    return "This will be the login page"


@app.route('/disconnect/')
def disconnect():
    return "This page will be the logout page"


@app.route('/profile/<int:user_id>/')
def profile(user_id):
    return "This will be the users profile page"


@app.route('/profile/create/')
def create_user():
    return "This will be the Create User page"


@app.route('/profile/<int:user_id>/edit/')
def edit_profile(user_id):
    return "This will be the Edit User page"


@app.route('/profile/<int:user_id>/delete/')
def delete_user(user_id):
    return "This will be the Delete User page"


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
