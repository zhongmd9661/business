"""测试 Office 文档解析支持"""
from src.document_parsing_pipeline.engine import ParseOptions, MinerUEngine, SUPPORTED_SUFFIXES


class TestOfficeDocumentSupport:
    """验证 Office 文档格式支持"""

    def test_office_suffixes_in_supported_list(self):
        """Office 后缀在支持列表中（不含点前缀）"""
        assert "docx" in SUPPORTED_SUFFIXES
        assert "xlsx" in SUPPORTED_SUFFIXES
        assert "pptx" in SUPPORTED_SUFFIXES

    def test_parse_options_for_office(self):
        """ParseOptions 配置适用于 Office 文档解析"""
        options = ParseOptions(
            method="auto",
            formula=False,
            table=True,
            return_images=False,
        )
        assert options.method == "auto"
        assert options.return_md is True

    def test_mineru_engine_import(self):
        """MinerUEngine 可正常导入和实例化"""
        engine = MinerUEngine()
        assert engine.options is not None
        assert engine._local_server is None
        assert engine._http_client is None
