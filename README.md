A simple CRUD app built with Flask. 
Users are able to authenticate using their Facebook and Google+ accounts.
Users are able to create, update and remove playlists and songs.
API endpoints are implemented for playlists and songs.


How to launch

Vagrant

Clone project
Make sure that you are in the cloned folder.
Run "vagrant up".
Once it's up, run "vagrant ssh".
In the terminal, type "cd /vagrant".
Once you are in, run pip install -r requirements.txt to make sure everything has gone as expected.
In the terminal, run "python project3.py".
Browse to localhost:5000 and sign in with your Facebook or Google+ account.

Virtualenv.
Install with pip install virtualenv.
In the cloned folder, type "virtualenv venv".
Then activate it by typing "source ven/bin/activate".
Run "pip install -r requirements.txt".
Once it's done, run "python project3.py"
Browse to localhost:5000 and sign in with your Facebook or Google+ account.