"""OCR 单文件识别 API — 上传文件后立即返回 Markdown 识别结果"""
import asyncio
import shutil
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException
from loguru import logger

from .config import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB, PROJECT_ROOT

router = APIRouter()

_ocr_semaphore = asyncio.Semaphore(3)
_temp_dir = PROJECT_ROOT / "data" / "ocr_temp"


@router.post("/ocr/recognize")
async def ocr_recognize(file: UploadFile = File(...)):
    """单文件 OCR 识别，返回 Markdown 格式结果。

    不需要认证，供独立 OCR 页面调用。
    支持 PDF、JPG、PNG、XML、DOCX、XLSX 格式。
    """
    # Validate
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型: {ext}")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"文件大小超过 {MAX_UPLOAD_SIZE_MB}MB 限制")

    async with _ocr_semaphore:
        # Save to temp dir
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_dir = _temp_dir / ts
        task_dir.mkdir(parents=True, exist_ok=True)
        file_path = task_dir / (file.filename or "unknown")
        file_path.write_bytes(content)

        try:
            result = await _run_ocr(file_path, task_dir)
        finally:
            # Cleanup temp dir
            if task_dir.exists():
                shutil.rmtree(task_dir, ignore_errors=True)

    return result


async def _run_ocr(file_path: Path, output_dir: Path) -> dict:
    """执行 OCR 并返回 markdown 内容"""
    start_time = time.time()

    try:
        from . import service

        # XML files: convert directly
        if file_path.suffix.lower() == ".xml":
            return await _handle_xml(file_path, output_dir, start_time)

        # Use MinerU engine directly
        engine = service.get_pipeline().engine
        from ..document_parsing_pipeline.engine import ParseOptions

        result = await engine.parse_file(
            file_path=file_path,
            output_dir=output_dir,
            seq=1,
            batch_name="ocr_single",
        )

        elapsed = time.time() - start_time

        if not result.success:
            raise RuntimeError(result.error or "OCR 识别失败")

        # Read the generated markdown
        md_content = _read_markdown(result.output_dir)

        return {
            "filename": file_path.name,
            "status": "success",
            "markdown": md_content,
            "elapsed": round(elapsed, 1),
        }

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"OCR failed for {file_path.name}: {e}")
        return {
            "filename": file_path.name,
            "status": "error",
            "error": str(e),
            "elapsed": round(elapsed, 1),
        }


async def _handle_xml(file_path: Path, output_dir: Path, start_time: float) -> dict:
    """处理 XML 发票文件"""
    from ..batch_processing.xml_to_md import xml_to_markdown
    from ..output_visualization.organizer import _generate_summary

    md_content = xml_to_markdown(file_path)
    summary_text = _generate_summary(md_content, "ocr_single")
    final_content = f"{summary_text}\n\n{md_content}"

    elapsed = time.time() - start_time

    return {
        "filename": file_path.name,
        "status": "success",
        "markdown": final_content,
        "elapsed": round(elapsed, 1),
    }


def _read_markdown(results_dir: Path) -> str:
    """从识别结果目录读取 Markdown 文件内容"""
    md_files = sorted(results_dir.glob("*.md"), key=lambda p: p.name)
    if not md_files:
        return "[未找到 Markdown 输出文件]"

    contents = []
    for md_file in md_files:
        contents.append(md_file.read_text(encoding="utf-8"))

    return "\n\n".join(contents)
