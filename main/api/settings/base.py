from pydantic import BaseSettings


class BaseAppSettings(BaseSettings):
    """
    Base application setting class.
    """

    app_env: str = "prod"
