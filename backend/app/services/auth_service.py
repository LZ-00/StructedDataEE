from app.core.config import settings


def verify_credentials(username: str, password: str) -> bool:
    return username == settings.default_username and password == settings.default_password
