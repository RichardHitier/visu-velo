import datetime

from flask import Flask


def create_app():
    app = Flask(__name__)

    @app.route('/')
    def home():
        time = datetime.datetime.now()
        return f"Hello Visu Velo at {time}"

    return app
