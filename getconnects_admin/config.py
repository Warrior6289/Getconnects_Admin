import os


class BaseConfig:
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

    def __init__(self) -> None:
        self.SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
        self.ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
        # Logo URL for sidebar and navigation
        self.LOGO_URL = os.getenv("LOGO_URL") or "/static/assets/images/logo.png"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    pass


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
