"""OCR 单文件识别 API — 上传文件后立即返回 Markdown 识别结果"""
import asyncio
import io
import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Query
from loguru import logger
from sqlalchemy.orm import Session

from .config import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB, PROJECT_ROOT
from .models_db import OCRRecord, get_db

router = APIRouter()

_ocr_semaphore = asyncio.Semaphore(3)
_temp_dir = PROJECT_ROOT / "data" / "ocr_temp"


# ==================== RapidOCR 引擎（PaddleOCR，GPU 加速） ====================

_ocr_instance = None
_ocr_device = None


def _get_ocr(device: str = "auto"):
    """获取 RapidOCR 单例（延迟加载），支持 device 切换"""
    global _ocr_instance, _ocr_device
    if _ocr_instance is None or _ocr_device != device:
        from rapidocr_onnxruntime import RapidOCR

        if device == "gpu":
            use_gpu = True
        elif device == "cpu":
            use_gpu = False
        else:
            try:
                import onnxruntime as ort
                use_gpu = "CUDAExecutionProvider" in ort.get_available_providers()
            except Exception:
                use_gpu = False

        _ocr_instance = RapidOCR(use_gpu=use_gpu, cls=True)
        _ocr_device = "gpu" if use_gpu else "cpu"
    return _ocr_instance


def _ocr_image_to_markdown(file_path: Path, device: str = "auto") -> tuple[str, list[dict], int, int]:
    """使用 RapidOCR 识别图片，返回 (markdown_text, ocr_blocks, img_w, img_h)"""
    from PIL import Image
    import numpy as np

    img = Image.open(file_path)
    img_w, img_h = img.size
    ocr = _get_ocr(device=device)
    result, _ = ocr(np.asarray(img))

    if not result:
        return "", [], img_w, img_h

    result_sorted = sorted(result, key=lambda x: x[0][0][1])
    lines = []
    blocks = []

    for word_info in result_sorted:
        box_points = word_info[0]
        text = word_info[1]
        score = word_info[2] if len(word_info) > 2 else 1.0
        lines.append(text)

        xs = [p[0] for p in box_points]
        ys = [p[1] for p in box_points]
        blocks.append({
            "text": text,
            "x": int(min(xs)), "y": int(min(ys)),
            "w": max(int(max(xs)) - int(min(xs)), 1),
            "h": max(int(max(ys)) - int(min(ys)), 1),
            "score": float(score) if score else 1.0,
        })

    markdown = "\n".join(lines)
    return markdown, blocks, img_w, img_h


def _ocr_image_file(file_path: Path, device: str = "auto") -> dict:
    """对图片文件执行 RapidOCR，返回包含 markdown 和 ocr_blocks 的结果字典"""
    try:
        markdown, blocks, img_w, img_h = _ocr_image_to_markdown(file_path, device=device)
        return {
            "markdown": markdown,
            "ocr_blocks": blocks,
            "ocr_lines": markdown.split("\n") if markdown else [],
            "img_width": img_w,
            "img_height": img_h,
            "engine": f"rapidocr-{_ocr_device}",
        }
    except ImportError:
        raise RuntimeError(
            "OCR 引擎未安装。请运行: pip install rapidocr-onnxruntime"
        )
    except Exception as e:
        raise RuntimeError(f"RapidOCR 识别失败: {str(e)}")


# ---------- 辅助函数 ----------

def _save_record(
    db: Session,
    username: str,
    serial_number: str,
    slot_name: str,
    original_filename: str,
    file_type: str,
    markdown: str,
    status: str,
    error_message: str = "",
    elapsed: float = 0,
    ocr_blocks: str = "",
    ocr_lines: str = "",
    img_width: int = 0,
    img_height: int = 0,
    engine: str = "",
) -> int:
    """保存 OCR 记录到数据库，返回 record_id"""
    record = OCRRecord(
        username=username,
        serial_number=serial_number,
        slot_name=slot_name,
        original_filename=original_filename,
        file_type=file_type,
        markdown=markdown,
        status=status,
        error_message=error_message,
        elapsed=elapsed,
        ocr_blocks=ocr_blocks,
        ocr_lines=ocr_lines,
        img_width=img_width,
        img_height=img_height,
        engine=engine,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record.id


def _detect_file_type(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}:
        return "image"
    if ext == ".pdf":
        return "pdf"
    if ext in {".doc", ".docx"}:
        return "doc"
    if ext == ".xml":
        return "xml"
    if ext == ".xlsx":
        return "xlsx"
    return "other"


# ---------- 单文件 OCR ----------

@router.post("/ocr/recognize")
async def ocr_recognize(
    file: UploadFile = File(...),
    serial_number: str = Form(""),
    slot_name: str = Form(""),
    username: str = Form(""),
    method: str = Form("ocr"),       # "ocr" (RapidOCR, 快) or "mineru" (MinerU, 通用)
    device: str = Form("gpu"),       # "auto", "cpu", "gpu" (仅 OCR 模式有效)
    db: Session = Depends(get_db),
):
    """单文件 OCR 识别，返回 Markdown 格式结果。

    支持可选参数 serial_number、slot_name、username 用于记录关联。
    支持 method: "ocr"=RapidOCR(PaddleOCR, 图片快), "mineru"=MinerU(PDF/文档通用)
    支持 device: "auto"/"cpu"/"gpu" (仅 OCR 模式有效)
    支持 PDF、JPG、PNG、XML、DOCX、XLSX 格式。
    """
    # Validate
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型: {ext}")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"文件大小超过 {MAX_UPLOAD_SIZE_MB}MB 限制")

    file_type = _detect_file_type(file.filename)

    async with _ocr_semaphore:
        # Save to temp dir
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_dir = _temp_dir / ts
        task_dir.mkdir(parents=True, exist_ok=True)
        file_path = task_dir / (file.filename or "unknown")
        file_path.write_bytes(content)

        try:
            result = await _run_ocr(file_path, task_dir, method=method, device=device)
        finally:
            # Cleanup temp dir
            if task_dir.exists():
                shutil.rmtree(task_dir, ignore_errors=True)

    # Save to database
    record_id = 0
    if username or serial_number:
        try:
            record_id = _save_record(
                db=db,
                username=username or "anonymous",
                serial_number=serial_number,
                slot_name=slot_name,
                original_filename=file.filename or "unknown",
                file_type=file_type,
                markdown=result.get("markdown", ""),
                status=result.get("status", "error"),
                error_message=result.get("error", ""),
                elapsed=result.get("elapsed", 0),
                ocr_blocks=json.dumps(result.get("ocr_blocks", []), ensure_ascii=False),
                ocr_lines=json.dumps(result.get("ocr_lines", []), ensure_ascii=False),
                img_width=result.get("img_width", 0) or 0,
                img_height=result.get("img_height", 0) or 0,
                engine=result.get("engine", "") or "",
            )
        except Exception as e:
            logger.error(f"Failed to save OCR record: {e}")

    result["record_id"] = record_id
    return result


# ---------- 批量 OCR ----------

@router.post("/ocr/batch-recognize")
async def ocr_batch_recognize(
    files: list[UploadFile] = File(...),
    serial_number: str = Form(""),
    slot_names: str = Form(""),
    username: str = Form(""),
    method: str = Form("ocr"),       # "ocr" (RapidOCR, 快) or "mineru" (MinerU, 通用)
    device: str = Form("gpu"),       # "auto", "cpu", "gpu" (仅 OCR 模式有效)
    db: Session = Depends(get_db),
):
    """批量识别多个文件，返回每个文件的 Markdown 结果 + 记录 ID 列表"""
    slot_name_list = [s.strip() for s in slot_names.split(",") if s.strip()] if slot_names else []
    results = []

    for idx, file in enumerate(files):
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            results.append({
                "filename": file.filename,
                "slot_name": slot_name_list[idx] if idx < len(slot_name_list) else "",
                "status": "error",
                "error": f"不支持的文件类型: {ext}",
                "record_id": 0,
            })
            continue

        content = await file.read()
        file_type = _detect_file_type(file.filename)

        async with _ocr_semaphore:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_") + str(idx)
            task_dir = _temp_dir / ts
            task_dir.mkdir(parents=True, exist_ok=True)
            file_path = task_dir / (file.filename or f"file_{idx}")
            file_path.write_bytes(content)

            try:
                result = await _run_ocr(file_path, task_dir, method=method, device=device)
            finally:
                if task_dir.exists():
                    shutil.rmtree(task_dir, ignore_errors=True)

        # Save record
        record_id = 0
        if username or serial_number:
            try:
                sn = slot_name_list[idx] if idx < len(slot_name_list) else ""
                record_id = _save_record(
                    db=db,
                    username=username or "anonymous",
                    serial_number=serial_number,
                    slot_name=sn,
                    original_filename=file.filename or "unknown",
                    file_type=file_type,
                    markdown=result.get("markdown", ""),
                    status=result.get("status", "error"),
                    error_message=result.get("error", ""),
                    elapsed=result.get("elapsed", 0),
                    ocr_blocks=json.dumps(result.get("ocr_blocks", []), ensure_ascii=False),
                    ocr_lines=json.dumps(result.get("ocr_lines", []), ensure_ascii=False),
                    img_width=result.get("img_width", 0) or 0,
                    img_height=result.get("img_height", 0) or 0,
                    engine=result.get("engine", "") or "",
                )
            except Exception as e:
                logger.error(f"Failed to save OCR record for {file.filename}: {e}")

        result["record_id"] = record_id
        result["slot_name"] = slot_name_list[idx] if idx < len(slot_name_list) else ""
        results.append(result)

    return {"records": results}


# ---------- 查询 OCR 记录 ----------

@router.get("/ocr/records")
async def query_ocr_records(
    serial_number: str = "",
    username: str = "",
    db: Session = Depends(get_db),
):
    """查询 OCR 记录，支持按用户名 + 流水号过滤"""
    query = db.query(OCRRecord)
    if serial_number:
        query = query.filter(OCRRecord.serial_number == serial_number)
    if username:
        query = query.filter(OCRRecord.username == username)
    records = query.order_by(OCRRecord.created_at.desc()).all()
    return [{
        "id": r.id,
        "username": r.username,
        "serial_number": r.serial_number,
        "slot_name": r.slot_name,
        "original_filename": r.original_filename,
        "file_type": r.file_type,
        "status": r.status,
        "elapsed": r.elapsed,
        "created_at": r.created_at,
    } for r in records]


@router.get("/ocr/records/{record_id}")
async def get_ocr_record(record_id: int, db: Session = Depends(get_db)):
    """获取单条 OCR 记录的完整 Markdown 内容"""
    record = db.query(OCRRecord).filter(OCRRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "记录未找到")
    return {
        "id": record.id,
        "username": record.username,
        "serial_number": record.serial_number,
        "slot_name": record.slot_name,
        "original_filename": record.original_filename,
        "file_type": record.file_type,
        "markdown": record.markdown,
        "status": record.status,
        "error_message": record.error_message,
        "elapsed": record.elapsed,
        "created_at": record.created_at,
        "ocr_blocks": json.loads(record.ocr_blocks) if record.ocr_blocks else [],
        "ocr_lines": json.loads(record.ocr_lines) if record.ocr_lines else [],
        "img_width": record.img_width or 0,
        "img_height": record.img_height or 0,
        "engine": record.engine or "",
    }


# ---------- 内部 OCR 执行 ----------

async def _run_ocr(file_path: Path, output_dir: Path, method: str = "ocr", device: str = "gpu") -> dict:
    """执行 OCR 并返回 markdown 内容

    method: "ocr" = RapidOCR (PaddleOCR, 图片快), "mineru" = MinerU (PDF/文档通用)
    device: "auto", "cpu", "gpu" (仅 OCR 模式有效)
    """
    start_time = time.time()
    file_type = _detect_file_type(file_path.name)

    # XML files: always use XML converter
    if file_path.suffix.lower() == ".xml":
        return await _handle_xml(file_path, output_dir, start_time)

    # Image files with RapidOCR method: use RapidOCR directly (fast, GPU-accelerated)
    if file_type == "image" and method == "ocr":
        try:
            ocr_result = _ocr_image_file(file_path, device=device)
            elapsed = time.time() - start_time
            return {
                "filename": file_path.name,
                "status": "success",
                "markdown": ocr_result["markdown"],
                "ocr_blocks": ocr_result["ocr_blocks"],
                "ocr_lines": ocr_result["ocr_lines"],
                "img_width": ocr_result["img_width"],
                "img_height": ocr_result["img_height"],
                "engine": ocr_result["engine"],
                "elapsed": round(elapsed, 1),
            }
        except Exception as e:
            elapsed = time.time() - start_time
            logger.warning(f"RapidOCR failed for {file_path.name}, falling back to MinerU: {e}")
            # Fall through to MinerU

    # PDF/DOC/other or MinerU method: use MinerU engine
    try:
        from . import service

        engine = service.get_pipeline().engine

        result = await engine.parse_file(
            file_path=file_path,
            output_dir=output_dir,
            seq=1,
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
