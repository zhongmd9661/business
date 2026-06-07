"""Download mineru models via modelscope"""
from modelscope import snapshot_download

print("Downloading model from modelscope...")
result = snapshot_download(
    "opendatalab/PDF-Extract-Kit-1.0",
)
print(f"Downloaded to: {result}")
