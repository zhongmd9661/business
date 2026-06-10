"""测试完整解析管道：引擎 + 输出组织"""
from pathlib import Path
from unittest.mock import patch

from src.batch_processing.collector import FileCollector
from src.output_visualization.organizer import OutputOrganizer, _generate_summary


def _fake_guess(path: Path) -> str:
    """Mock guess_suffix_by_path: return extension without dot (matches SUPPORTED_SUFFIXES)"""
    return path.suffix.lower().lstrip(".")


class TestParsePipeline:
    """验证文件收集到输出组织的完整流程"""

    def test_collect_and_organize_flow(self, tmp_path):
        """文件收集 → 序号分配 → 输出组织的端到端流程"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "001_test_doc.pdf").touch()
        (input_dir / "002_test_image.jpg").touch()
        (input_dir / "003_test_docx.docx").touch()

        with patch("src.batch_processing.collector.guess_suffix_by_path", side_effect=_fake_guess):
            files = FileCollector.collect(input_dir)
        assert len(files) == 3

        sequences = FileCollector.assign_sequences(files)
        assert sequences == [1, 2, 3]

        output_base = tmp_path / "output"
        output_base.mkdir()
        out_dir = OutputOrganizer.create_output_dir(output_base)
        out_dir.mkdir(parents=True)
        assert out_dir.exists()
        assert len(out_dir.name) == 15

    def test_summary_generation_with_batch_context(self):
        """摘要生成正确融合批次上下文"""
        content = """# 测试文档
<table><tr><td>接待日期</td><td>2026-03-15</td></tr>
<tr><td>预计支出金额</td><td>2,500.00</td></tr></table>
正文内容..."""
        summary = _generate_summary(content, batch_summary="差旅报销")
        assert "## 摘要" in summary
        assert "差旅报销" in summary
        assert "2026-03-15" in summary
        assert "2,500.00" in summary

    def test_office_file_in_collection(self, tmp_path):
        """Office 文档被正确收集"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "001_report.docx").touch()
        (input_dir / "002_data.xlsx").touch()
        (input_dir / "003_slide.pptx").touch()

        with patch("src.batch_processing.collector.guess_suffix_by_path", side_effect=_fake_guess):
            files = FileCollector.collect(input_dir)
        suffixes = [f.suffix.lower() for f in files]
        assert ".docx" in suffixes
        assert ".xlsx" in suffixes
        assert ".pptx" in suffixes

    def test_mixed_format_collection(self, tmp_path):
        """混合格式文件按序号正确排序"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "003_table.xlsx").touch()
        (input_dir / "001_report.pdf").touch()
        (input_dir / "002_photo.jpg").touch()

        with patch("src.batch_processing.collector.guess_suffix_by_path", side_effect=_fake_guess):
            files = FileCollector.collect(input_dir)
        names = [f.name for f in files]
        assert names[0].startswith("001_")
        assert names[1].startswith("002_")
        assert names[2].startswith("003_")
