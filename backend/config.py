# filepath: c:\Users\d.tolkunov\CodeRepository\INGD\backend\config.py
import os
from urllib.parse import quote_plus # Import quote_plus for password encoding

class Config:
    """Base configuration class."""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-for-development-only")
    SQLALCHEMY_DATABASE_URI = build_db_uri() # Use the helper function
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    # Adjust testing DB URI if needed, maybe use a separate test MySQL DB or SQLite
    SQLALCHEMY_DATABASE_URI = "sqlite:///test_ingd.db"

class ProductionConfig(Config):
    """Production configuration."""
    # Production-specific settings might override the base URI if needed
    pass

# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}