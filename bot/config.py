from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str
    zai_api_key: str
    zai_model: str = "glm-4.6v"
    database_url: str
    webapp_url: str = "http://localhost:5173"
    free_scans_per_month: int = 3
    scan_price_stars: int = 1

    model_config = {"env_file": ".env"}


def get_settings() -> Settings:
    return Settings()
