"""测试 document_parsing_pipeline 模块的 engine 组件"""
import pytest
from pathlib import Path
from src.document_parsing_pipeline.engine import ParseOptions, ParseResult


class TestParseOptions:
    """测试 ParseOptions 数据类"""

    def test_default_values(self):
        """验证默认配置值"""
        options = ParseOptions()
        assert options.backend == "pipeline"
        assert options.lang == ("ch",)
        assert options.method == "auto"
        assert options.formula is True
        assert options.table is True
        assert options.image_analysis is True
        assert options.return_images is False
        assert options.return_md is True

    def test_custom_values(self):
        """验证自定义配置值"""
        options = ParseOptions(
            backend="test_backend",
            lang=("en",),
            method="test_method",
            formula=False,
            table=False,
            image_analysis=False,
            return_images=False,
            return_md=False,
        )
        assert options.backend == "test_backend"
        assert options.lang == ("en",)
        assert options.method == "test_method"
        assert options.formula is False
        assert options.table is False
        assert options.image_analysis is False
        assert options.return_images is False
        assert options.return_md is False


class TestParseResult:
    """测试 ParseResult 数据类"""

    def test_create_result(self):
        """验证 ParseResult 对象创建"""
        result = ParseResult(
            file_path=Path("/test/file.pdf"),
            seq=1,
            output_dir=Path("/test/output"),
            success=True,
            elapsed=10.5,
        )
        assert result.file_path == Path("/test/file.pdf")
        assert result.seq == 1
        assert result.output_dir == Path("/test/output")
        assert result.success is True
        assert result.elapsed == 10.5
        assert result.error is None

    def test_create_failed_result(self):
        """验证失败的 ParseResult 对象"""
        result = ParseResult(
            file_path=Path("/test/file.pdf"),
            seq=1,
            output_dir=Path("/test/output"),
            success=False,
            elapsed=5.0,
            error="Test error",
        )
        assert result.success is False
        assert result.error == "Test error"
