import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    database_url: str = "sqlite:///./data/app.db"
    generated_policies_dir: str = "./generated_policies"
    chroma_persist_dir: str = "./data/chroma"
    cors_origins: str = "http://localhost:3000,http://localhost:8501"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Dynamically add Railway public domain to CORS origins
railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
if railway_domain:
    railway_origin = f"https://{railway_domain}"
    if railway_origin not in settings.cors_origins:
        settings.cors_origins = f"{settings.cors_origins},{railway_origin}"

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates" / "jinja2"
REGULATORY_DATA_DIR = BASE_DIR / "regulatory_data"
GENERATED_DIR = Path(settings.generated_policies_dir)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
