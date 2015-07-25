from flask import Flask, request, url_for, render_template, flash
from sqlalchemy.orm import sessionmaker
from sqlalchemy import asc, create_engine

from database_setup import base, Users

app = Flask(__name__)


# Connect to Database and create database session
engine = create_engine('sqlite:///test.db')
base.metadata.bind = engine

db_session = sessionmaker(bind=engine)
session = db_session()


@app.route('/')
def home():
    users = session.query(Users).order_by(asc(Users.name))
    return render_template('home.html', users=users)


@app.route('/login/')
def login():
    return "This will be the login page"


@app.route('/disconnect/')
def disconnect():
    return "This page will be the logout page"


@app.route('/profile/<int:user_id>/')
def profile(user_id):
    users = session.query(Users).order_by(asc(name=Users)).all()
    return render_template(url_for('profile', user_id=user_id, users=users))


@app.route('/create/', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        user_to_create = Users(name=request.form['name'],
                               email=request.form['email'])
        session.add(user_to_create)
        flash('The user {} was successfully created'.format(
            user_to_create.name))
        session.commit()
        return render_template(url_for('home'))
    else:
        return render_template('create-user.html')


@app.route('/profile/<int:user_id>/edit/')
def edit_profile(user_id):
    return "This will be the Edit Users page"


@app.route('/profile/<int:user_id>/delete/')
def delete_user(user_id):
    return "This will be the Delete Users page"


if __name__ == '__main__':
    app.secret_key = 'secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
