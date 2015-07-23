from flask import Flask

app = Flask(__name__)


@app.route('/')
def home():
    return "This will be the home page"


@app.route('/profile/<int:user_id>/')
def profile(user_id):
    return "This will be the users profile page"


@app.route('/profile/<int:user_id>/edit/')
def edit_profile(user_id):
    return "This will be the Edit User page"


@app.route('/profile/<int:user_id>/delete/')
def delete_user(user_id):
    return "This will be the Delete User page"


@app.route('/profile/create/')
def create_user():
    return "This will be the Create User page"

if __name__ == '__main__':
    app.run()
