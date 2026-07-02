import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "CodeAtlas"
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "codeatlas")
    WORKSPACE_DIR: str = os.getenv("WORKSPACE_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../workspace_temp")))
    MAX_FILE_COUNT: int = int(os.getenv("MAX_FILE_COUNT", "1000"))
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    ALLOWED_EXTENSIONS: set = {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".md", ".txt"}

    class Config:
        env_file = ".env"

settings = Settings()
