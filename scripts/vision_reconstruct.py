"""视觉重建报表脚本 - 独立于原有 batch_parse.py
功能：将仿真手机截图集还原为一张完整的、可滚动的结构化 Excel 报表。
Usage: python -m scripts.vision_reconstruct --input <dir> --output <dir>
"""
import argparse
import asyncio
import os
import pathlib
from datetime import datetime
from loguru import logger

import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from src.batch_processing.collector import FileCollector
from src.document_parsing_pipeline.llm_vision_engine import LlmVisionEngine
from src.document_parsing_pipeline.splicing_engine import SplicingEngine
from src.output_visualization.excel_reporter import ExcelReporter

async def reconstruct_batch(input_dir: pathlib.Path, output_dir: pathlib.Path, vision_engine: LlmVisionEngine):
    """执行单批次的视觉重建流程"""
    batch_name = input_dir.name
    logger.info(f"{'=' * 60}")
    logger.info(f"Reconstructing Vision Report for batch: {batch_name}")
    logger.info(f"{'=' * 60}")

    files = FileCollector.collect(input_dir)
    if not files:
        logger.warning(f"No supported images found in {input_dir}")
        return

    # 1. 碎片化结构提取 (Vision Extraction)
    fragments = []
    for i, f in enumerate(files):
        logger.info(f"[{batch_name}] Parsing image {i+1}/{len(files)}: {f.name}")
        try:
            frag = vision_engine.parse_image(f)
            fragments.append(frag)
        except Exception as e:
            logger.error(f"Failed to parse {f.name}: {e}")

    if not fragments:
        logger.error(f"No valid data extracted from batch {batch_name}")
        return

    # 2. 语义拼接重建 (Semantic Splicing)
    logger.info(f"[{batch_name}] Aligning fragments and rebuilding virtual matrix...")
    splicer = SplicingEngine()
    global_table = splicer.reconstruct(fragments)
    headers = fragments[0].headers if fragments else []

    # 3. 专业报表导出 (Excel Export)
    reporter = ExcelReporter()
    excel_path = output_dir / f"{batch_name}_reconstructed_report.xlsx"
    try:
        reporter.generate(global_table, headers, excel_path)
        logger.info(f"[{batch_name}] Success! Reconstructed report saved to: {excel_path}")
    except Exception as e:
        logger.error(f"Failed to export Excel for {batch_name}: {e}")

async def main():
    parser = argparse.ArgumentParser(description="仿真手机截图 $\rightarrow$ 完整结构化报表重建")
    parser.add_argument("--input", type=str, required=True, help="输入图片文件夹路径 (或包含多个子文件夹的目录)")
    parser.add_argument("--output", type=str, required=True, help="输出结果目录")
    args = parser.parse_args()

    input_path = pathlib.Path(args.input)
    output_path = pathlib.Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    # 初始化视觉引擎
    vision_engine = LlmVisionEngine()
    vision_engine.start()

    try:
        if input_path.is_dir():
            # 检查是否是单个批次或包含多个子文件夹
            subdirs = [d for d in input_path.iterdir() if d.is_dir()]
            if subdirs:
                logger.info(f"Found {len(subdirs)} batches in {input_path}")
                for batch_dir in sorted(subdirs):
                    await reconstruct_batch(batch_dir, output_path, vision_engine)
            else:
                # 将输入目录本身视为一个批次
                await reconstruct_batch(input_path, output_path, vision_engine)

    finally:
        vision_engine.stop()

if __name__ == "__main__":
    asyncio.run(main())
