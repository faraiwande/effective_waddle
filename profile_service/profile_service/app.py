import os
import logging
from flask import Flask
from flask_migrate import Migrate
from profile_service.models.user_profile_model import db
from profile_service.flask_config import Config
from profile_service.routes.user_profiles import (
    reg_bp,
    user_information_bp,
    role_bp,
    profile_bp
)

import debugpy
migrate = Migrate()

def create_app():
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logging.info("Initializing User Profile Service...")

    # Create Flask app instance
    app = Flask(__name__)
    
    # Load configuration from object
    app.config.from_object(Config)
    
    # Set database URI (with fallback for development)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///ridebase.db'
    )

    # Register Blueprints
    app.register_blueprint(reg_bp)
    app.register_blueprint(user_information_bp)
    app.register_blueprint(role_bp)
    app.register_blueprint(profile_bp)

    # Health check endpoint
    @app.route('/')
    def index():
        return {"message": "User Profile Service is up and running!"}, 200

     # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    if app.config.get("ENV") != "production":
        with app.app_context():
            logging.info("Creating database tables (non-production environment)...")
            db.create_all()
                       
    app.debug = True 
    return app

