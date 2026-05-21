from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    secret_key: str = "sdweb-dev-secret-change-in-production"
    access_token_expire_hours: int = 24
    default_username: str = "root"
    default_password: str = "123456"


settings = Settings()
