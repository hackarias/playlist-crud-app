# A simple CRUD app built with Flask
Users are able to authenticate using their Facebook and Google+ accounts.

Users are able to create, update and remove playlists and songs.

API endpoints are implemented for playlists and songs.


# How to launch #

## Vagrant ##
1. Open a terminal and navigate to where you want to clone the project.
1. Clone project by running "git clone https://gloison@bitbucket.org/gloison/project3.git".
1. Make sure that you are in the cloned folder.
1. In the terminal, run "vagrant up".
1. Once it's up, run "vagrant ssh".
1. In the terminal, type "cd /vagrant".
1. In the terminal, run "python project3.py".
1. Browse to localhost:5000 in your browser and sign in with your Facebook or Google+ account.

## Virtualenv ##
1. Install by entering "pip install virtualenv" in the terminal.
1. Open a terminal and navigate to where you want to clone the project.
1. Clone project by running "git clone https://gloison@bitbucket.org/gloison/project3.git".
1. In the cloned folder, type "virtualenv venv" to start using it.
1. Then activate it by typing "source venv/bin/activate".
1. Run "pip install -r requirements.txt" to install all dependencies.
1. Once it's done, run "python project3.py"
1. Browse to localhost:5000 in your browser and sign in with your Facebook or Google+ account.


# TODO #
* Add some style and make it pretty.
* Implement deletion of content using post request.
* Add support for images.
* Add more endpoints (XML or RSS).