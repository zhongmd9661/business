"""Convert rule documents (docx) to Markdown using MinerU Engine"""
import asyncio
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.document_parsing_pipeline import MinerUEngine, ParseOptions
from loguru import logger


async def convert():
    base_dir = Path(__file__).parent.parent
    input_dir = base_dir / "00规则制度"
    output_dir = base_dir / "00规则制度_md"
    tmp_dir = base_dir / "00规则制度_tmp"

    files = sorted(input_dir.glob("*.docx"))
    if not files:
        logger.warning(f"No .docx files found in {input_dir}")
        return

    logger.info(f"Found {len(files)} rule document(s) to convert")

    engine = MinerUEngine(ParseOptions())
    await engine.start()
    try:
        for i, file_path in enumerate(files, 1):
            logger.info(f"[{i}/{len(files)}] Parsing {file_path.name}")
            result = await engine.parse_file(file_path, tmp_dir, i)
            if result.success:
                logger.info(f"  -> parsed")
            else:
                logger.error(f"  -> Failed: {result.error}")
    finally:
        await engine.stop()

    # Move markdown files to output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    md_dir = tmp_dir / "识别结果"
    if md_dir.exists():
        for md_file in md_dir.glob("*.md"):
            dest = output_dir / md_file.stem.with_suffix(".md").name
            shutil.move(str(md_file), str(dest))
            logger.info(f"  -> {dest.name}")

    # Clean up temporary files
    shutil.rmtree(tmp_dir, ignore_errors=True)
    logger.info(f"Output: {output_dir}")


if __name__ == "__main__":
    asyncio.run(convert())
