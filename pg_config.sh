#!/usr/bin/env bash
apt-get -qqy update
apt-get -qqy install postgresql python-psycopg2
apt-get -qqy install python-sqlalchemy
apt-get -qqy install python-pip
pip install werkzeug
pip install flask
pip install Flask-Login
pip install oauth2client
pip install requests
pip install httplib2

