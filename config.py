import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production-2026")
    
    # This automatically picks up the secure PostgreSQL URL from Render environment variables
    DATABASE_PATH = os.environ.get("DATABASE_URL")
    
    MODEL_DIR = os.path.join(BASE_DIR, "model")
    CHARTS_DIR = os.path.join(BASE_DIR, "static", "images", "charts")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB
