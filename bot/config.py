from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str
    openrouter_api_key: str
    openrouter_model: str = "anthropic/claude-sonnet-4-5-20250929"
    database_url: str
    free_scans_per_month: int = 3
    scan_price_stars: int = 1

    model_config = {"env_file": ".env"}


def get_settings() -> Settings:
    return Settings()
