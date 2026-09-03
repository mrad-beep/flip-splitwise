from flask import Flask
from flask_cors import CORS
from .extensions import db


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///splitwise.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    CORS(app)  # frontend is a separate app hitting us over HTTP, so allow it

    from . import models  # noqa: F401  (must be imported before create_all)
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()

    return app
