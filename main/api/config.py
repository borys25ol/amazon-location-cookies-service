from functools import lru_cache

from main.api.settings.app import AppSettings
from main.api.settings.production import ProdAppSettings


@lru_cache
def get_app_settings() -> AppSettings:
    """
    Return application config.
    """
    return ProdAppSettings()
