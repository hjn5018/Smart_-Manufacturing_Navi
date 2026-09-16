import os
from pydantic_settings import BaseSettings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, ".env")

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    DATABASE_URL: str
    AUTO_CREATE_TABLES: bool = False
    DEVICE_CONTROL_KEY: str | None = None
    DEVICE_CONTROL_KEYS: str | None = None
    DEVICE_PROVISIONING_KEY: str | None = None
    COMMAND_ACK_TIMEOUT_SECONDS: int = 3
    COMMAND_RESULT_TIMEOUT_SECONDS: int = 10
    BOARD_HEARTBEAT_STALE_SECONDS: int = 15

    model_config = {
        "env_file": ENV_PATH,
        "env_file_encoding": "utf-8"
    }

settings = Settings()
