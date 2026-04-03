from flask import Flask
from config import DevelopmentConfig


def create_app(config_class=DevelopmentConfig):
    """
    Application factory pattern.
    This mirrors production Flask setups used in airline IT systems
    where different configs are loaded for dev / staging / prod.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register blueprints
    from app.routes.availability import availability_bp
    from app.routes.booking import booking_bp

    app.register_blueprint(availability_bp, url_prefix="/api/v1")
    app.register_blueprint(booking_bp, url_prefix="/api/v1")

    return app
