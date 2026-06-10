"""清理旧的输出目录 - 支持保留最近N个或按时间清理"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


def get_output_dirs(base_dir: Path) -> list[tuple[Path, datetime]]:
    """获取输出目录列表，按时间从旧到新排序"""
    dirs = []
    for d in base_dir.iterdir():
        if d.is_dir():
            dirs.append((d, datetime.fromtimestamp(d.stat().st_mtime)))
    return sorted(dirs, key=lambda x: x[1])


def cleanup_by_count(base_dir: Path, keep: int, dry_run: bool = False) -> int:
    """保留最近 keep 个目录，清理其余"""
    dirs = get_output_dirs(base_dir)
    to_remove = dirs[:-keep] if len(dirs) > keep else []

    if not to_remove:
        logger.info(f"无需清理 - 当前 {len(dirs)} 个目录，保留 {keep} 个")
        return 0

    removed = 0
    for d, mt in to_remove:
        ts = mt.strftime("%Y-%m-%d %H:%M:%S")
        if dry_run:
            logger.info(f"[模拟] 将删除: {d.name} (修改于 {ts})")
        else:
            import shutil
            shutil.rmtree(d)
            logger.info(f"已删除: {d.name} (修改于 {ts})")
        removed += 1

    logger.info(f"清理完成 - {'模拟删除 ' if dry_run else '已删除 '}{removed} 个目录，保留 {keep} 个")
    return removed


def cleanup_by_days(base_dir: Path, days: int, dry_run: bool = False) -> int:
    """清理 N 天前的目录"""
    from datetime import timedelta

    cutoff = datetime.now() - timedelta(days=days)
    dirs = get_output_dirs(base_dir)
    to_remove = [(d, mt) for d, mt in dirs if mt < cutoff]

    if not to_remove:
        logger.info(f"无需清理 - 所有目录均在 {days} 天内")
        return 0

    removed = 0
    for d, mt in to_remove:
        ts = mt.strftime("%Y-%m-%d %H:%M:%S")
        if dry_run:
            logger.info(f"[模拟] 将删除: {d.name} (修改于 {ts})")
        else:
            import shutil
            shutil.rmtree(d)
            logger.info(f"已删除: {d.name} (修改于 {ts})")
        removed += 1

    logger.info(f"清理完成 - {'模拟删除 ' if dry_run else '已删除 '}{removed} 个目录")
    return removed


def list_dirs(base_dir: Path) -> None:
    """列出所有输出目录"""
    dirs = get_output_dirs(base_dir)
    if not dirs:
        logger.info(f"{base_dir} 下无输出目录")
        return

    logger.info(f"输出目录 ({len(dirs)} 个):")
    for i, (d, mt) in enumerate(dirs, 1):
        size = sum(p.stat().st_size for p in d.rglob("*") if p.is_file())
        size_str = f"{size / 1024 / 1024:.1f}MB" if size > 1024 * 1024 else f"{size / 1024:.1f}KB"
        logger.info(f"  {i}. {d.name} — {mt.strftime('%Y-%m-%d %H:%M:%S')} ({size_str})")


def main():
    parser = argparse.ArgumentParser(
        description="清理 data/已识别/ 下的旧输出目录",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/cleanup_outputs.py              # 列出所有输出目录
  python scripts/cleanup_outputs.py --keep 5     # 保留最近 5 个
  python scripts/cleanup_outputs.py --days 30    # 清理 30 天前的
  python scripts/cleanup_outputs.py --keep 3 --dry-run  # 模拟清理
        """,
    )
    parser.add_argument(
        "-k", "--keep",
        type=int,
        default=None,
        help="保留最近的 N 个输出目录",
    )
    parser.add_argument(
        "-d", "--days",
        type=int,
        default=None,
        help="清理 N 天前的输出目录",
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="模拟运行，不实际删除",
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="列出所有输出目录",
    )
    parser.add_argument(
        "-b", "--base-dir",
        type=Path,
        default=None,
        help="输出根目录，默认为 data/已识别/",
    )

    args = parser.parse_args()
    base_dir = args.base_dir or Path(__file__).parent.parent / "data" / "已识别"

    if not base_dir.exists():
        logger.warning(f"目录不存在: {base_dir}")
        return

    if args.list or (not args.keep and not args.days):
        list_dirs(base_dir)
        return

    if args.keep is not None and args.keep < 1:
        logger.error("保留数量必须 >= 1")
        return

    if args.keep is not None:
        cleanup_by_count(base_dir, args.keep, args.dry_run)
    elif args.days is not None:
        cleanup_by_days(base_dir, args.days, args.dry_run)


if __name__ == "__main__":
    main()
