from flask import Flask, request,render_template, redirect
from profile_service.flask_config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config())
    return app