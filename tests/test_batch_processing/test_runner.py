"""测试 batch_processing 模块的 runner 组件"""
import pytest
from pathlib import Path
from src.batch_processing.runner import BatchRunner
from src.document_parsing_pipeline.engine import ParseResult


class TestBatchRunner:
    """测试 BatchRunner 类"""

    def test_print_header(self, caplog):
        """验证头部信息输出"""
        with caplog.at_level("INFO"):
            test_files = [Path("/test/001_file.pdf"), Path("/test/002_file.jpg")]
            BatchRunner.print_header("20260607_100000", Path("/test/output"), test_files)
            # 验证日志中包含关键信息
            assert "Batch parse started at 20260607_100000" in caplog.text
            assert "Output directory: " in caplog.text
            assert "Found 2 file(s) to parse" in caplog.text

    def test_log_progress(self, caplog):
        """验证进度日志"""
        with caplog.at_level("INFO"):
            BatchRunner.log_progress(1, 10, 1, "test_file.pdf", "Parsing")
            assert "[1/10]" in caplog.text
            assert "10%" in caplog.text
            assert "#1" in caplog.text
            assert "Parsing: test_file.pdf" in caplog.text

    def test_print_summary(self, caplog):
        """验证汇总报告"""
        with caplog.at_level("INFO"):
            # 创建测试结果
            results = [
                ParseResult(
                    file_path=Path("/test/001_file.pdf"),
                    seq=1,
                    output_dir=Path("/test/output/001_file"),
                    success=True,
                    elapsed=10.5,
                ),
                ParseResult(
                    file_path=Path("/test/002_file.jpg"),
                    seq=2,
                    output_dir=Path("/test/output/002_file"),
                    success=False,
                    elapsed=5.0,
                    error="Test error",
                ),
            ]
            BatchRunner.print_summary(results, 15.5)
            # 验证日志中包含关键信息
            assert "Batch parse complete!" in caplog.text
            assert "Total time: 15.5s" in caplog.text
            assert "Files processed: 2/2" in caplog.text
            assert "OK" in caplog.text
            assert "FAIL: Test error" in caplog.text
