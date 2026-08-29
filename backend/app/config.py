import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Determine the project root (parent of backend/)
# __file__ is at backend/app/config.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = Path(__file__).resolve().parent.parent

# Try loading .env from multiple locations, in order of preference
env_locations = [
    BACKEND_ROOT / ".env",      # backend/.env  (where uvicorn is run from)
    PROJECT_ROOT / ".env",    # project-root/.env
    Path.cwd() / ".env",       # current working dir/.env
]

loaded_from = None
for env_path in env_locations:
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path), override=True)
        loaded_from = str(env_path)
        break

# Print to stderr so it shows in terminal even with uvicorn logging
if loaded_from:
    print(f"[config] Loaded .env from: {loaded_from}", file=sys.stderr)
else:
    print(f"[config] WARNING: No .env file found. Searched:", file=sys.stderr)
    for p in env_locations:
        print(f"[config]   - {p}", file=sys.stderr)

class Settings:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
    MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-4o-mini").strip()
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
    GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "").strip()
    GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", "8000"))
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./code_review.db")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "100000"))
    MAX_FILES_PER_REVIEW = int(os.getenv("MAX_FILES_PER_REVIEW", "50"))
    ENABLE_CROSS_VALIDATION = os.getenv("ENABLE_CROSS_VALIDATION", "true").lower() == "true"

    @classmethod
    def validate(cls) -> list:
        errors = []

        if not cls.OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY is not set. Add it to backend/.env or project-root/.env")
        elif not cls.OPENROUTER_API_KEY.startswith(("sk-or-", "sk-")):
            masked = cls.OPENROUTER_API_KEY[:4] + "..." + cls.OPENROUTER_API_KEY[-4:] if len(cls.OPENROUTER_API_KEY) > 8 else "[too short]"
            errors.append(f"OPENROUTER_API_KEY looks invalid. Expected 'sk-or-v1-...' format (got: {masked})")

        if not cls.MODEL_NAME:
            errors.append("MODEL_NAME is not set.")

        return errors

    @classmethod
    def debug_info(cls) -> dict:
        key = cls.OPENROUTER_API_KEY
        return {
            "key_set": bool(key),
            "key_length": len(key),
            "key_prefix": key[:10] + "..." if len(key) > 10 else key,
            "model": cls.MODEL_NAME,
            "env_loaded_from": loaded_from,
        }

settings = Settings()
