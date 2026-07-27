"""Download mineru models to project models/ directory.

Models are saved locally in the project directory so that the entire project
can be moved without re-downloading.

Usage:
    python scripts/download_models.py
"""
import os
from pathlib import Path

# Set cache directory to project-level models/ folder
project_root = Path(__file__).resolve().parent.parent
model_cache = project_root / "models"
model_cache.mkdir(exist_ok=True)

os.environ["MODELSCOPE_CACHE"] = str(model_cache)

from modelscope import snapshot_download

print(f"Downloading models to: {model_cache}")
result = snapshot_download(
    "opendatalab/PDF-Extract-Kit-1.0",
    cache_dir=str(model_cache),
)
print(f"Models saved to: {result}")
