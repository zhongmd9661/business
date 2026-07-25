"""Web 服务配置 — 环境变量驱动"""
import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Database — ensure data directory exists
_data_dir = PROJECT_ROOT / "data"
_data_dir.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{_data_dir / 'web_service.db'}",
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
