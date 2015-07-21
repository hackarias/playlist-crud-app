from flask import Flask

app = Flask(__name__)


@app.route('/')
def home():
    return "This will be the home page"


@app.route('/profile/')
def profile():
    return "This will be the users profile page"


if __name__ == '__main__':
    app.run()
