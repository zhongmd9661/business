"""输出组织 - 时间戳目录、zip 解压、结果管理、目录扁平化、序号对应、摘要生成"""
import re
import shutil
from datetime import datetime
from pathlib import Path

from loguru import logger

from mineru.cli import api_client as _api_client


class OutputOrganizer:
    @staticmethod
    def create_output_dir(base_dir: Path) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return base_dir / ts

    @staticmethod
    def reorganize(raw_dir: Path, target_dir: Path, seq: int, stem: str, batch_summary: str = None) -> Path:
        """将 MinerU 解压后的目录扁平化并生成摘要。

        原始: {raw_dir}/{stem}/auto/{stem}.md
        目标: {target_dir}/识别结果/{seq}_{stem}.md
        """
        results_dir = target_dir / "识别结果"
        results_dir.mkdir(parents=True, exist_ok=True)

        stem_dir = raw_dir / stem
        md_dir = None

        # 查找解析方法子目录（auto, office, pipeline, hybrid_*, vlm 等）
        if stem_dir.is_dir():
            for sub in stem_dir.iterdir():
                if sub.is_dir():
                    if (sub / f"{stem}.md").exists():
                        md_dir = sub
                        break
            # 没找到带 md 文件的子目录，直接用 stem_dir
            if md_dir is None:
                md_dir = stem_dir

        if md_dir is None:
            md_dir = stem_dir

        # 移动 Markdown 文件并重命名
        md_src = md_dir / f"{stem}.md"
        if md_src.exists():
            md_dst = results_dir / f"{seq}_{stem}.md"
            _add_summary(md_dst, md_src, batch_summary)
            logger.info(f"  -> {md_dst.name} (with summary)")
        else:
            # 没有 md 文件时查找任意 md
            for m in md_dir.glob("*.md"):
                new_name = f"{seq}_{stem}.md"
                _add_summary(results_dir / new_name, m, batch_summary)
                m.rename(results_dir / new_name)

        # 移动中间 JSON 文件（如果返回了）
        _move_middle_json(md_dir, stem, results_dir, seq)

        # 清理空目录
        if stem_dir.is_dir():
            for d in sorted(stem_dir.iterdir(), key=lambda p: str(p), reverse=True):
                if d.is_dir() and not any(d.iterdir()):
                    d.rmdir()

        return results_dir

    @staticmethod
    def extract(result_zip_path: Path, output_dir: Path) -> Path:
        out_dir = output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        _api_client.safe_extract_zip(result_zip_path, out_dir)
        result_zip_path.unlink(missing_ok=True)
        return out_dir


def _add_summary(target_md: Path, source_md: Path, batch_summary: str = None) -> None:
    """读取解析后的 Markdown，在顶部追加摘要章节后写入目标文件。

    batch_summary: 批次级摘要，由用户在启动时一次性输入。
    """
    content = source_md.read_text(encoding="utf-8")
    summary = _generate_summary(content, batch_summary)
    final = f"{summary}\n\n{content}"
    target_md.write_text(final, encoding="utf-8")
    source_md.unlink(missing_ok=True)


def _generate_summary(content: str, batch_summary: str = None) -> str:
    """生成文档摘要。

    batch_summary: 用户在启动时输入的批次摘要（如"差旅报销"），作为整体背景。
    文档自身信息自动提取：标题、日期、金额等关键字段。
    """
    lines = content.strip().split("\n")
    title = lines[0].lstrip("# ").strip() if lines else "文档"

    # 去除 HTML 标签以便提取文本
    plain_text = re.sub(r"<[^>]+>", " ", content)

    # 匹配常见关键字段
    key_info = []
    patterns = [
        (r"单据状态\s*(.+?)(?:\s*$)", "状态"),
        (r"流程状态\s*(.+?)(?:\s*$)", "流程"),
        (r"接待日期\s*(\d{4}[-/]\d{2}[-/]\d{2})", "接待日期"),
        (r"创建日期\s*(\d{4}[-/]\d{2}[-/]\d{2})", "创建日期"),
        (r"预计支出金额\s*([\d,]+\.?\d*)", "金额"),
        (r"宴请支出\s*([\d,]+\.?\d*)", "支出"),
        (r"报账单标题\s*(.+?)(?:\s*$)", "标题"),
        (r"使用人\s*(.+?)(?:\s*$)", "使用人"),
        (r"来宾单位\s*(.+?)(?:\s*$)", "来宾单位"),
        (r"来源系统单号\s*(\S+)", "单号"),
    ]

    for pat, label in patterns:
        m = re.search(pat, plain_text)
        if m:
            val = m.group(1).strip()
            if val and len(val) <= 30:
                key_info.append(f"{label}: {val}")
            if len(key_info) >= 4:
                break

    parts = []
    if batch_summary:
        parts.append(f"批次: {batch_summary}")

    if key_info:
        parts.append(", ".join(key_info))
    else:
        # 简单摘要：取前 3 行非空非标题非表内容
        preview = []
        for line in lines[:15]:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("<table"):
                preview.append(stripped)
                if len(preview) >= 3:
                    break
        if preview:
            parts.append("; ".join(preview))

    # 标题始终放在最前
    if title != "文档" and (not parts or parts[0] != title):
        parts.insert(0, title)

    summary = "## 摘要\n\n" + " — ".join(parts)
    return summary


def _move_middle_json(search_dir: Path, stem: str, results_dir: Path, seq: int) -> None:
    """查找并移动 MinerU 的中间 JSON 文件到识别结果目录。

    MinerU 返回的 JSON 文件名可能是 {stem}_middle.json 或 {stem}.json，
    可能直接放在 search_dir 下或在某个子目录中。
    """
    json_candidates = [f"{stem}_middle.json", f"{stem}.json"]

    # 先在直接目录下找
    for candidate in json_candidates:
        src = search_dir / candidate
        if src.exists():
            dst = results_dir / f"{seq}_{stem}.json"
            shutil.copy2(src, dst)
            logger.info(f"  -> {dst.name}")
            return

    # 在子目录中递归查找
    for jfile in search_dir.rglob("*middle*.json"):
        dst = results_dir / f"{seq}_{stem}.json"
        shutil.copy2(jfile, dst)
        logger.info(f"  -> {dst.name}")
        return
