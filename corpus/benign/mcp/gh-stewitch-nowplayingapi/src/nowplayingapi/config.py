from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Centralized application configuration.
    """
    
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    
    TARGET_PROCESS_NAMES: set[str] = {
        "qqmusic.exe",
        "cloudmusic.exe",
        "spotify.exe"
    }
    
    # The results of the audio scan will be cached for this many seconds.
    CACHE_TTL_SECONDS: int = 3
    
    # Load some server config from .env file.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

settings = Settings()