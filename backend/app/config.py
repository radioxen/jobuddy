import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: str = ""

    # LLM
    OPENAI_MODEL: str = "gpt-5.2-2025-12-11"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/jobuddy.db"

    # File paths
    BASE_DIR: str = str(Path(__file__).resolve().parent.parent)
    UPLOAD_DIR: str = ""
    GENERATED_DIR: str = ""
    BROWSER_PROFILE_DIR: str = ""

    # Playwright
    PLAYWRIGHT_HEADLESS: bool = False

    # Application
    MAX_CONCURRENT_APPLICATIONS: int = 3
    JOB_FIT_SCORE_THRESHOLD: float = 50.0
    MAX_SEARCH_RESULTS: int = 25

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "..",
            ".env",
        )
        env_file_encoding = "utf-8"

    def model_post_init(self, __context):
        if not self.UPLOAD_DIR:
            self.UPLOAD_DIR = os.path.join(self.BASE_DIR, "data", "uploads")
        if not self.GENERATED_DIR:
            self.GENERATED_DIR = os.path.join(self.BASE_DIR, "data", "generated")
        if not self.BROWSER_PROFILE_DIR:
            self.BROWSER_PROFILE_DIR = os.path.join(
                self.BASE_DIR, "data", "browser_profiles"
            )
        # Ensure directories exist
        for d in [self.UPLOAD_DIR, self.GENERATED_DIR, self.BROWSER_PROFILE_DIR]:
            os.makedirs(d, exist_ok=True)


settings = Settings()
