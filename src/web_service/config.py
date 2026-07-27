"""Web 服务配置 — 环境变量驱动"""
import json
import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{PROJECT_ROOT / 'data' / 'web_service.db'}",
)

# JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours

# File upload
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".xml", ".docx", ".xlsx"}
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"

# Rule sync
RULE_SYNC_INTERVAL_MIN = int(os.getenv("RULE_SYNC_INTERVAL_MIN", "2"))
RULES_DIR = PROJECT_ROOT / "00规则制度" / "00综合部业务招待费"

# MinerU
MINERU_MODEL_SOURCE = os.getenv("MINERU_MODEL_SOURCE", "modelscope")
MINERU_DEVICE = os.getenv("MINERU_DEVICE", "cuda")
MAX_CONCURRENT_OCR = int(os.getenv("MAX_CONCURRENT_OCR", "3"))

# --- App Settings (persistent JSON config) ---
DATA_DIR = PROJECT_ROOT / "data"
APP_SETTINGS_FILE = DATA_DIR / "app_settings.json"

# LLM defaults — written to settings.json if file missing
_DEFAULT_SETTINGS = {
    "anthropic_base_url": os.environ.get("ANTHROPIC_BASE_URL", "http://192.168.231.1:1235"),
    "anthropic_auth_token": os.environ.get("ANTHROPIC_AUTH_TOKEN", "lmstudio"),
    "llm_model": os.environ.get("LLM_MODEL", "Qwen/Qwen3.6-27B"),
}


def init_app_settings():
    """Load settings from JSON file into os.environ (or create defaults)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not APP_SETTINGS_FILE.exists():
        APP_SETTINGS_FILE.write_text(json.dumps(_DEFAULT_SETTINGS, ensure_ascii=False, indent=2), encoding="utf-8")
    _apply_app_settings()


def _apply_app_settings():
    """Read app_settings.json and update os.environ so all modules pick it up."""
    try:
        data = json.loads(APP_SETTINGS_FILE.read_text(encoding="utf-8"))
        mapping = {
            "anthropic_base_url": "ANTHROPIC_BASE_URL",
            "anthropic_auth_token": "ANTHROPIC_AUTH_TOKEN",
            "llm_model": "LLM_MODEL",
        }
        for key, env_name in mapping.items():
            val = data.get(key)
            if val is not None:
                os.environ[env_name] = str(val)
    except Exception:
        pass  # Fallback to existing env vars


def get_app_settings():
    """Return current settings dict."""
    try:
        return json.loads(APP_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return _DEFAULT_SETTINGS.copy()


def save_app_settings(data: dict):
    """Persist settings to JSON file and apply to os.environ."""
    mapping = {
        "anthropic_base_url": "ANTHROPIC_BASE_URL",
        "anthropic_auth_token": "ANTHROPIC_AUTH_TOKEN",
        "llm_model": "LLM_MODEL",
    }
    for key in mapping:
        val = data.get(key)
        if val is not None:
            os.environ[mapping[key]] = str(val)
    APP_SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
