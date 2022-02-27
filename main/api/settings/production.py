from main.api.settings.app import AppSettings


class ProdAppSettings(AppSettings):
    """
    Production application settings.
    """

    class Config(AppSettings.Config):
        env_file = ".env"
