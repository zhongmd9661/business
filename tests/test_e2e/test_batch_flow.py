"""端到端测试：验证批量处理流程（不启动 MinerU 服务器，mock 文件类型检测）"""
import zipfile
from pathlib import Path
from unittest.mock import patch

from src.batch_processing.collector import FileCollector
from src.batch_processing.runner import BatchRunner
from src.document_parsing_pipeline.engine import ParseResult
from src.output_visualization.organizer import OutputOrganizer


def _fake_guess(path: Path) -> str:
    """Mock guess_suffix_by_path: return extension without dot (matches SUPPORTED_SUFFIXES format)"""
    return path.suffix.lower().lstrip(".")


class TestBatchFlow:
    """模拟批量处理流程"""

    def test_full_batch_workflow(self, tmp_path):
        """收集 → 序号分配 → 输出目录创建 → 结果汇总"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "001_invoice.pdf").touch()
        (input_dir / "002_receipt.jpg").touch()
        (input_dir / "003_report.docx").touch()
        (input_dir / "readme.txt").write_text("not supported")

        with patch("src.batch_processing.collector.guess_suffix_by_path", side_effect=_fake_guess):
            files = FileCollector.collect(input_dir)
        assert len(files) == 3  # txt 被过滤

        sequences = FileCollector.assign_sequences(files)
        assert sequences == [1, 2, 3]

        output_base = tmp_path / "output"
        output_base.mkdir()
        out_dir = OutputOrganizer.create_output_dir(output_base)
        out_dir.mkdir(parents=True)
        assert out_dir.parent == output_base

        results = []
        for i, f in enumerate(files):
            results.append(ParseResult(
                file_path=f,
                seq=sequences[i],
                output_dir=out_dir / f"{sequences[i]}_{f.stem}",
                success=True,
                elapsed=1.0,
            ))

        BatchRunner.print_summary(results, 3.0)

        src_dir = out_dir / "src"
        src_dir.mkdir(exist_ok=True)
        md_dir = out_dir / "results"
        md_dir.mkdir(exist_ok=True)
        assert src_dir.exists()
        assert md_dir.exists()

    def test_error_handling_in_batch(self, tmp_path):
        """单个文件失败不影响整体流程"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "001_good.pdf").touch()
        (input_dir / "002_bad.pdf").touch()
        (input_dir / "003_good.jpg").touch()

        with patch("src.batch_processing.collector.guess_suffix_by_path", side_effect=_fake_guess):
            files = FileCollector.collect(input_dir)
        sequences = FileCollector.assign_sequences(files)

        output_base = tmp_path / "output"
        output_base.mkdir()
        out_dir = OutputOrganizer.create_output_dir(output_base)

        results = []
        for i, f in enumerate(files):
            success = f.name != "002_bad.pdf"
            results.append(ParseResult(
                file_path=f,
                seq=sequences[i],
                output_dir=out_dir,
                success=success,
                elapsed=1.0,
                error="simulated error" if not success else None,
            ))

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[1].error == "simulated error"
        assert results[2].success is True

    def test_auto_sequence_assignment(self, tmp_path):
        """无序号文件自动分配序号"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "001_first.pdf").touch()
        (input_dir / "no_number.jpg").touch()
        (input_dir / "003_third.pdf").touch()

        with patch("src.batch_processing.collector.guess_suffix_by_path", side_effect=_fake_guess):
            files = FileCollector.collect(input_dir)
        sequences = FileCollector.assign_sequences(files)
        # collect() sorts by seq number, no-seq files go last (key=999)
        # order: 001_first(1), 003_third(3), no_number(0→auto)
        assert sequences[0] == 1
        assert sequences[1] == 3
        assert sequences[2] == 4  # auto-incremented beyond max(1,3)

    def test_zip_extraction_workflow(self, tmp_path):
        """zip 文件自动解压后参与处理"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        pdf_content = b"%PDF-1.4 fake pdf content for testing"
        with zipfile.ZipFile(input_dir / "batch.zip", "w") as zf:
            zf.writestr("001_document.pdf", pdf_content)

        with patch("src.batch_processing.collector.guess_suffix_by_path", side_effect=_fake_guess):
            files = FileCollector.collect(input_dir)
        assert len(files) >= 1
        assert any("001_document" in f.name for f in files)
        assert not (input_dir / "batch.zip").exists()

    def test_office_in_batch_workflow(self, tmp_path):
        """Office 文档在批量流程中正确参与"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "001_spec.docx").touch()
        (input_dir / "002_budget.xlsx").touch()
        (input_dir / "003_contract.pdf").touch()

        with patch("src.batch_processing.collector.guess_suffix_by_path", side_effect=_fake_guess):
            files = FileCollector.collect(input_dir)
        assert len(files) == 3

        types = [f.suffix.lower() for f in files]
        assert types == [".docx", ".xlsx", ".pdf"]
