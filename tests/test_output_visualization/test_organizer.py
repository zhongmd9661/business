"""测试 output_visualization 模块的 organizer 组件"""
import pytest
from pathlib import Path
from src.output_visualization.organizer import OutputOrganizer, _generate_summary


class TestOutputOrganizer:
    """测试 OutputOrganizer 类"""

    def test_create_output_dir(self, tmp_path):
        """验证输出目录创建"""
        output_dir = OutputOrganizer.create_output_dir(tmp_path)
        # 验证目录路径格式正确
        assert output_dir.parent == tmp_path
        # 验证时间戳格式 (YYYYMMDD_HHMMSS)
        assert len(output_dir.name) == 15  # 20260607_100000 的长度
        assert output_dir.name[8] == "_"   # 第9个字符应该是下划线
        # 验证目录名是数字和下划线组成
        assert output_dir.name[:8].isdigit()
        assert output_dir.name[9:].isdigit()


class TestGenerateSummary:
    """测试摘要生成"""

    def test_summary_with_batch_summary(self):
        """验证带批次摘要的生成"""
        content = """# 业务招待申请
基础信息
<table><tr><td>接待日期</td><td>2026-02-27</td></tr><tr><td>预计支出金额</td><td>1,050.00</td></tr></table>"""
        result = _generate_summary(content, batch_summary="差旅报销-清远")
        assert "## 摘要" in result
        assert "差旅报销-清远" in result
        assert "2026-02-27" in result
        assert "1,050.00" in result

    def test_summary_without_batch_summary(self):
        """验证不带批次摘要的生成"""
        content = """# 合同文件
<table><tr><td>创建日期</td><td>2026-01-15</td></tr></table>"""
        result = _generate_summary(content)
        assert "## 摘要" in result
        assert "合同文件" in result
        assert "2026-01-15" in result

    def test_summary_fallback_to_preview(self):
        """验证无表格时取前几行作为预览"""
        content = """# 测试文档
第一段内容
第二段内容
第三段内容"""
        result = _generate_summary(content)
        assert "## 摘要" in result
        assert "第一段内容" in result
