"""Batch parse all files in data/input using MinerU Engine"""
import argparse
import asyncio
import time
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.batch_processing.runner import BatchRunner
from src.batch_processing.collector import FileCollector
from src.batch_processing.xml_to_md import xml_to_markdown
from src.document_parsing_pipeline import MinerUEngine, ParseOptions
from src.document_parsing_pipeline.engine import ParseResult
from src.output_visualization.organizer import OutputOrganizer
from src.expense_review_comprehensive import (
    FieldExtractor,
    ComprehensiveChecker,
    ComprehensiveReporter,
    WebhookNotifier,
    BatchReviewReport,
)
from loguru import logger


def get_batch_summary() -> str:
    """获取用户输入的批次摘要"""
    parser = argparse.ArgumentParser(description="批量 OCR 解析")
    parser.add_argument("-s", "--summary", type=str, default=None,
                       help="批次摘要，如：差旅报销")
    args = parser.parse_args()
    if args.summary:
        return args.summary
    try:
        summary = input("请输入批次摘要（如：差旅报销）: ").strip()
        return summary if summary else "batch"
    except (EOFError, UnicodeDecodeError):
        return "batch"


def convert_xml(file_path: Path, output_dir: Path, seq: int, batch_summary: str = None) -> ParseResult:
    """转换 XML 发票为 Markdown，输出到识别结果目录"""
    start = time.time()
    stem = file_path.stem
    try:
        md_content = xml_to_markdown(file_path)
        from src.output_visualization.organizer import _generate_summary
        summary_text = _generate_summary(md_content, batch_summary)
        final_content = f"{summary_text}\n\n{md_content}"

        results_dir = output_dir / "识别结果"
        results_dir.mkdir(parents=True, exist_ok=True)
        md_file = results_dir / f"{seq}_{stem}.md"
        md_file.write_text(final_content, encoding="utf-8")
        return ParseResult(
            file_path=file_path,
            seq=seq,
            output_dir=results_dir,
            success=True,
            elapsed=time.time() - start,
        )
    except Exception as e:
        return ParseResult(
            file_path=file_path,
            seq=seq,
            output_dir=output_dir / "识别结果",
            success=False,
            elapsed=time.time() - start,
            error=str(e),
        )


async def parse_all():
    base_dir = Path(__file__).parent.parent
    input_dir = base_dir / "data" / "input"

    # 获取批次摘要
    summary = get_batch_summary()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 输出和归档统一使用 已识别 目录
    output_dir = base_dir / "data" / "已识别" / f"{summary}_{ts}"
    archive_dir = output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # 收集文件（含 zip 自动解压）
    files = FileCollector.collect(input_dir)
    if not files:
        logger.warning(f"No supported files in {input_dir}")
        return

    BatchRunner.print_header(ts, output_dir, files)

    engine = MinerUEngine(ParseOptions())
    results = []
    run_start = datetime.now()

    # 分配序号（无序号文件自动递增）
    sequences = FileCollector.assign_sequences(files)

    await engine.start()
    try:
        for i, file_path in enumerate(files, 1):
            seq = sequences[i - 1]
            BatchRunner.log_progress(i, len(files), seq, file_path.name, "Parsing")

            if file_path.suffix.lower() == ".xml":
                result = convert_xml(file_path, output_dir, seq, summary)
            else:
                result = await engine.parse_file(file_path, output_dir, seq, summary)
            results.append(result)

            BatchRunner.log_progress(i, len(files), seq, file_path.name, "Done")

            # 成功处理的文件移至源文件目录，带序号前缀
            if result.success:
                src_dir = output_dir / "源文件"
                src_dir.mkdir(parents=True, exist_ok=True)
                file_path.rename(src_dir / f"{seq}_{file_path.name}")
    finally:
        await engine.stop()

    total_elapsed = (datetime.now() - run_start).total_seconds()
    BatchRunner.print_summary(results, total_elapsed)

    # 清理临时 _raw 目录
    import shutil
    raw_dir = output_dir / "_raw"
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
        logger.info("Cleaned up temporary _raw directory")

    # ---- 审核：解析后对批次运行全面审核 ----
    extractor = FieldExtractor()
    checker = ComprehensiveChecker()
    reporter = ComprehensiveReporter()
    notifier = WebhookNotifier("http://localhost:9999/hook")

    all_fields = []
    filenames = []
    results_dir = output_dir / "识别结果"

    if results_dir.is_dir():
        for md_file in sorted(results_dir.glob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
                fields = extractor.extract(content)
                all_fields.append(fields)
                filenames.append(md_file.name)
            except Exception as e:
                logger.warning(f"Review failed for {md_file.name}: {e}")

    # 批次统一审核
    if all_fields:
        batch_report = checker.check_batch_review(filenames, all_fields)
        batch_report.batch_name = summary

        # 简要摘要日志
        batch_summary = reporter.format_batch_summary(batch_report)
        logger.info(f"批次审核: {batch_summary}")

        # 输出批次报告
        report_text = reporter.format_batch_text(batch_report)
        report_path = output_dir / "审核报告.txt"
        report_path.write_text(report_text, encoding="utf-8")
        logger.info(f"批次审核报告: {report_path}")

        # Webhook 通知：基于总体判定触发
        if batch_report.has_high_risk:
            # 将 BatchFinding 转为 Finding 用于 webhook
            from src.expense_review_comprehensive.models import Finding
            findings_for_webhook = [
                Finding(f.category, f.rule, f.clause, f.level, f.message)
                for f in batch_report.all_findings
            ]
            notifier.notify(findings_for_webhook, summary)

    logger.info(f"Output: {output_dir}")


if __name__ == "__main__":
    asyncio.run(parse_all())
