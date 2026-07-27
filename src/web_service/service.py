"""业务逻辑 — 审核任务编排：OCR → 提取 → 审核"""
import json
import os
import re
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger


def _fix_fasttext_chinese_path():
    """Workaround: FastText C++ library cannot open files on paths with non-ASCII (Chinese) characters.

    Copy the fast_langdetect model to a temp ASCII-only location and patch the module to use it.
    """
    try:
        import fast_langdetect.ft_detect.infer as infer_mod

        src = infer_mod.LOCAL_SMALL_MODEL_PATH
        if not src.exists():
            return
        # Only needed if path contains non-ASCII
        try:
            str(src).encode("ascii")
            return  # Already ASCII path, no fix needed
        except UnicodeEncodeError:
            pass

        # Copy model to temp dir with ASCII path
        tmp_dir = tempfile.mkdtemp(prefix="ft_fix_")
        dst = Path(tmp_dir) / src.name
        shutil.copy2(str(src), str(dst))
        infer_mod.LOCAL_SMALL_MODEL_PATH = dst
        # Also patch model cache key so it reloads
        infer_mod._model_cache._models.clear()
        logger.info(f"Patched fast_langdetect model path: {dst}")
    except Exception as e:
        logger.warning(f"Failed to patch fasttext Chinese path workaround: {e}")


# Pipeline imports
from ..batch_processing.collector import FileCollector
from ..batch_processing.xml_to_md import xml_to_markdown
from ..document_parsing_pipeline import MinerUEngine, ParseOptions
from ..document_parsing_pipeline.engine import ParseResult
from ..expense_review_comprehensive import (
    ComprehensiveChecker,
    ComprehensiveReporter,
    FieldExtractor,
    LlmFieldExtractor,
    ExtractedFields,
)
from ..output_visualization.organizer import _generate_summary

from .config import PROJECT_ROOT


class ReviewPipeline:
    """审核管线 — 封装 OCR + 提取 + 审核"""

    def __init__(self, engine: MinerUEngine, use_llm: bool = False, dynamic_rules: list[dict] | None = None):
        self.engine = engine
        self.use_llm = use_llm
        self._checker = None  # Lazy-init with dynamic rules
        self._dynamic_rules = dynamic_rules or []

    async def process_batch(
        self,
        batch_dir: Path,
        batch_name: str,
    ) -> tuple[Path, str]:
        """处理一个批次，返回 (output_dir, report_text)"""
        files = FileCollector.collect(batch_dir)
        if not files:
            return Path(), "无支持的文件"

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = PROJECT_ROOT / "data" / "已识别" / f"{batch_name}_{ts}"
        output_dir.mkdir(parents=True, exist_ok=True)

        sequences = FileCollector.assign_sequences(files)
        results = []

        for i, file_path in enumerate(files, 1):
            seq = sequences[i - 1]
            if file_path.suffix.lower() == ".xml":
                result = self._convert_xml(file_path, output_dir, seq, batch_name)
            else:
                result = await self.engine.parse_file(file_path, output_dir, seq, batch_name)
            results.append(result)

            if result.success:
                src_dir = output_dir / "源文件"
                src_dir.mkdir(parents=True, exist_ok=True)
                file_path.rename(src_dir / f"{seq}_{file_path.name}")

        # Clean temp dir
        raw_dir = output_dir / "_raw"
        if raw_dir.exists():
            shutil.rmtree(raw_dir)

        # Field extraction
        all_fields, filenames = self._extract_fields(output_dir)

        # Write field results
        self._write_field_results(output_dir / "识别结果", filenames, all_fields)

        # Batch review
        report_text = ""
        if all_fields:
            report_text = self._batch_review(output_dir, filenames, all_fields, batch_name)

        return output_dir, report_text

    def _convert_xml(
        self, file_path: Path, output_dir: Path, seq: int, batch_name: str
    ) -> ParseResult:
        start = time.time()
        try:
            md_content = xml_to_markdown(file_path)
            summary_text = _generate_summary(md_content, batch_name)
            final_content = f"{summary_text}\n\n{md_content}"

            results_dir = output_dir / "识别结果"
            results_dir.mkdir(parents=True, exist_ok=True)
            md_file = results_dir / f"{seq}_{file_path.stem}.md"
            md_file.write_text(final_content, encoding="utf-8")
            return ParseResult(
                file_path=file_path, seq=seq, output_dir=results_dir,
                success=True, elapsed=time.time() - start,
            )
        except Exception as e:
            return ParseResult(
                file_path=file_path, seq=seq,
                output_dir=output_dir / "识别结果",
                success=False, elapsed=time.time() - start, error=str(e),
            )

    def _extract_fields(
        self, output_dir: Path
    ) -> tuple[list[ExtractedFields], list[str]]:
        all_fields: list[ExtractedFields] = []
        filenames: list[str] = []
        results_dir = output_dir / "识别结果"
        if not results_dir.is_dir():
            return all_fields, filenames

        md_files = [
            f for f in results_dir.glob("*.md")
            if not f.name.startswith("字段提取结果")
        ]
        def _seq(f):
            m = re.match(r"(\d+)_", f.name)
            return int(m.group(1)) if m else 9999
        md_files.sort(key=_seq)

        if self.use_llm and LlmFieldExtractor is not None:
            extractor = LlmFieldExtractor()
            extractor.start()
            try:
                for md_file in md_files:
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        fields = extractor.extract(content)
                        fields.source_file = md_file.name
                        all_fields.append(fields)
                        filenames.append(md_file.name)
                    except Exception as e:
                        logger.warning(f"LLM extract failed for {md_file.name}: {e}")
            finally:
                extractor.stop()
        else:
            extractor = FieldExtractor()
            for md_file in md_files:
                try:
                    content = md_file.read_text(encoding="utf-8")
                    fields = extractor.extract(content)
                    fields.source_file = md_file.name
                    all_fields.append(fields)
                    filenames.append(md_file.name)
                except Exception as e:
                    logger.warning(f"Extract failed for {md_file.name}: {e}")

        return all_fields, filenames

    def _batch_review(
        self, output_dir: Path, filenames: list[str],
        all_fields: list[ExtractedFields], batch_name: str,
    ) -> str:
        review_start = time.time()
        checker = ComprehensiveChecker(dynamic_rules=self._dynamic_rules)
        reporter = ComprehensiveReporter()
        batch_report = checker.check_batch_review(filenames, all_fields)
        batch_report.batch_name = batch_name
        batch_report.elapsed_seconds = time.time() - review_start

        report_text = reporter.format_batch_text(batch_report)
        (output_dir / "审核报告.txt").write_text(report_text, encoding="utf-8")

        report_md = reporter.format_batch_md(batch_report)
        (output_dir / "审核报告.md").write_text(report_md, encoding="utf-8")

        return report_text

    def _write_field_results(
        self, results_dir: Path, filenames: list[str],
        all_fields: list[ExtractedFields],
    ) -> None:
        if not all_fields or not results_dir.is_dir():
            return

        field_labels = {
            "reception_date": "招待日期", "invoice_date": "发票日期",
            "apply_date": "申请日期", "payment_date": "支付日期",
            "invoice_amount": "发票金额", "actual_amount": "实际金额",
            "per_person_amount": "人均金额", "alcohol_price": "酒水价格",
            "souvenir_amount": "纪念品金额", "guest_count": "招待对象人数",
            "companion_count": "陪同人数", "handler": "经办人",
            "payee": "收款人", "personnel_level": "人员级别",
            "reception_type": "招待类型", "host_unit": "招待单位",
            "seller_name": "销售方", "merchant_name": "商户全称",
            "department": "部门", "reimbursement_no": "报账单号",
            "invoice_no": "发票号码", "transaction_no": "交易单号",
            "merchant_order_no": "商户单号",
        }
        bool_fields = {
            "payment_voucher_present": "支付凭证",
            "payment_statement_present": "支付流水",
            "official_letter_present": "往来公函",
            "invoice_verified": "发票查验",
            "expense_detail_list_present": "费用明细清单",
            "grid_allocation_signed": "网格分摊表签章",
            "has_alcohol_tobacco": "烟酒标志",
            "bulk_alcohol": "批量购买酒水",
            "gift_suspected": "礼品嫌疑",
            "tourism_suspected": "旅游嫌疑",
            "is_cash_payment": "现金支付",
            "has_prepaid": "预存签单",
            "is_holiday_reported": "节假日报备",
        }

        def _fmt(val, fn=None):
            if val is None:
                return None
            if isinstance(val, datetime):
                if fn == "payment_date":
                    return val.strftime("%Y-%m-%d %H:%M:%S")
                return val.strftime("%Y-%m-%d")
            return val

        # JSON
        json_data = []
        for fn, flds in zip(filenames, all_fields):
            source = re.sub(r"^\d+_", "", fn)
            entry = {"filename": fn, "source_file": source}
            for attr in field_labels:
                entry[attr] = _fmt(getattr(flds, attr, None), attr)
            for attr in bool_fields:
                entry[attr] = getattr(flds, attr, None)
            json_data.append(entry)

        json_path = results_dir / "字段提取结果.json"
        json_path.write_text(
            json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Markdown
        md_lines = ["# 字段提取结果汇总\n"]
        for fn, flds in zip(filenames, all_fields):
            source = re.sub(r"^\d+_", "", fn)
            md_lines.append(f"## {fn}\n")
            md_lines.append("| 字段 | 提取值 | 数据来源 |")
            md_lines.append("|------|--------|----------|")
            for attr, label in field_labels.items():
                v = getattr(flds, attr, None)
                if v is not None:
                    md_lines.append(f"| {label} | {_fmt(v, attr)} | {source} |")
            for attr, label in bool_fields.items():
                v = getattr(flds, attr, False)
                if v:
                    md_lines.append(f"| {label} | 有 | {source} |")
            md_lines.append("")

        md_path = results_dir / "字段提取结果.md"
        md_path.write_text("\n".join(md_lines), encoding="utf-8")


# --- Global singleton ---

_engine: Optional[MinerUEngine] = None
_pipeline: Optional[ReviewPipeline] = None


def _load_rules_from_db() -> list[dict]:
    """从数据库加载启用的审核规则"""
    from .models_db import SessionLocal, AuditRule
    from .rule_cache import get_rule_cache

    db = SessionLocal()
    try:
        cache = get_rule_cache()
        count = cache.load(db)
        logger.info(f"Loaded {count} audit rules from database")
        return cache.rules
    except Exception as e:
        logger.error(f"Failed to load audit rules: {e}")
        return []
    finally:
        db.close()


async def start_engine():
    global _engine, _pipeline
    # Fix FastText Chinese path issue BEFORE importing MinerU (which triggers fast_langdetect)
    _fix_fasttext_chinese_path()

    use_llm = os.environ.get("USE_LLM_EXTRACTOR", "").lower() in ("1", "true", "yes")
    _engine = MinerUEngine(ParseOptions())
    await _engine.start()
    # Load dynamic rules from database
    dynamic_rules = _load_rules_from_db()
    _pipeline = ReviewPipeline(_engine, use_llm, dynamic_rules)
    logger.info("MinerU engine started")


async def stop_engine():
    global _engine
    if _engine:
        await _engine.stop()
        logger.info("MinerU engine stopped")


def get_pipeline() -> ReviewPipeline:
    return _pipeline


def reload_rules() -> int:
    """热重载审核规则 — 规则变更后调用"""
    from .rule_cache import get_rule_cache

    cache = get_rule_cache()
    cache.invalidate()
    rules = _load_rules_from_db()
    if _pipeline:
        _pipeline._dynamic_rules = rules
        logger.info(f"Reloaded {len(rules)} audit rules")
    return len(rules)
