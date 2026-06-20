import os
import re
from pathlib import Path
from urllib.parse import quote

BASE_DIR = Path(__file__).resolve().parent
IS_VERCEL = "VERCEL" in os.environ or os.getenv("FLASK_ENV") == "production"


def _build_db_url():
    """
    Build the database URL from available environment variables.
    Priority:
      1. DATABASE_URL (explicit full URL)
      2. SUPABASE_URL + SUPABASE_DB_PASSWORD (auto-construct from Supabase project)
      3. Fallback to local SQLite
    """
    # 1. Explicit DATABASE_URL takes priority
    explicit = os.getenv("DATABASE_URL", "")
    if explicit:
        return explicit

    # 2. Auto-construct from SUPABASE_URL + SUPABASE_DB_PASSWORD
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_pass = os.getenv("SUPABASE_DB_PASSWORD", "")
    if supabase_url and supabase_pass:
        match = re.search(r'https?://([^.]+)\.supabase\.co', supabase_url)
        if match:
            project_ref = match.group(1)
            encoded_pass = quote(supabase_pass, safe="")
            return f"postgresql://postgres:{encoded_pass}@db.{project_ref}.supabase.co:5432/postgres"

    # 3. Fallback to local SQLite
    if IS_VERCEL:
        return "/tmp/projectassign.db"
    return str(BASE_DIR / "instance" / "projectassign.db")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key_project_assign_2026_sdlfjksdf")
    DATABASE = _build_db_url()
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "/tmp/uploads" if IS_VERCEL else str(BASE_DIR / "instance" / "uploads"))
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
