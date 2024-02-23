from pydantic_settings import BaseSettings


class BaseAppSettings(BaseSettings):
    """
    Base application setting class.
    """

    app_env: str = "prod"

    scrapyrt_url: str
