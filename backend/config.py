import os
from backend.config_manager import get_config_value
from backend.data_dir import get_data_dir


class Config:
    """Flask application configuration.

    Only includes settings consumed by Flask or its extensions.
    LLM and integration settings are managed through config_manager.py
    and read on demand by route handlers.
    """

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(get_data_dir() / "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # Logging level — read by create_app() in app.py
    LOG_LEVEL = get_config_value("logging.level", "INFO")
