"""批量处理运行器 - 进度显示、耗时统计、汇总报告"""
from datetime import datetime
from pathlib import Path

from loguru import logger


class BatchRunner:
    @staticmethod
    def print_header(timestamp: str, output_dir: Path, files: list[Path]) -> None:
        from .collector import FileCollector

        logger.info("=" * 60)
        logger.info(f"Batch parse started at {timestamp}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Found {len(files)} file(s) to parse")
        logger.info("-" * 60)
        for i, f in enumerate(files, 1):
            seq = FileCollector.get_seq_number(f)
            logger.info(f"  #{i} [{seq}] {f.name}")
        logger.info("=" * 60)

    @staticmethod
    def log_progress(i: int, total: int, seq: int, filename: str, action: str) -> None:
        pct = int(i / total * 100)
        now = datetime.now().strftime("%H:%M:%S")
        logger.info(f"  [{i}/{total}] {pct}% | {now} #{seq} {action}: {filename}")

    @staticmethod
    def print_summary(results: list, total_elapsed: float) -> None:
        logger.info("=" * 60)
        logger.info("Batch parse complete!")
        logger.info(f"Total time: {total_elapsed:.1f}s ({total_elapsed / 60:.1f}min)")
        logger.info(f"Files processed: {len(results)}/{len(results)}")
        logger.info("-" * 60)
        for i, r in enumerate(results, 1):
            status = "OK" if r.success else f"FAIL: {r.error}"
            logger.info(f"  #{i} [{r.seq}] {r.file_path.name} ({r.elapsed:.1f}s) {status}")
        logger.info("=" * 60)
