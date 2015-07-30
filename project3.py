from flask import Flask, request, url_for, render_template, flash, redirect
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
        flash('The user {} was successfully created'.format(
            user_to_create.name))
        session.commit()
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
        return redirect(url_for('home'))
    else:
        return render_template('delete-user.html', deleted=user_to_delete)


if __name__ == '__main__':
    app.secret_key = 'secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
