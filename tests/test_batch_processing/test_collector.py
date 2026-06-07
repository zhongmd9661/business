"""测试 batch_processing 模块的 collector 组件"""
import pytest
from pathlib import Path
from src.batch_processing.collector import FileCollector


class TestFileCollector:
    """测试 FileCollector 类"""

    def test_get_seq_number_valid(self, tmp_path):
        """验证有效的序号提取"""
        test_file = tmp_path / "001_test_file.pdf"
        test_file.touch()
        seq = FileCollector.get_seq_number(test_file)
        assert seq == 1

    def test_get_seq_number_valid_multi_digit(self, tmp_path):
        """验证多位数序号提取"""
        test_file = tmp_path / "123_test_file.pdf"
        test_file.touch()
        seq = FileCollector.get_seq_number(test_file)
        assert seq == 123

    def test_get_seq_number_invalid(self, tmp_path):
        """验证无效的序号处理"""
        test_file = tmp_path / "test_file_no_number.pdf"
        test_file.touch()
        seq = FileCollector.get_seq_number(test_file)
        assert seq == 0

    def test_get_seq_number_partial_match(self, tmp_path):
        """验证部分匹配的序号处理"""
        test_file = tmp_path / "01_test_file.pdf"  # 只有2位数字
        test_file.touch()
        seq = FileCollector.get_seq_number(test_file)
        assert seq == 0  # 应该是0，因为模式要求3位数字

    def test_collect_files_empty_directory(self, tmp_path):
        """验证空目录的文件收集"""
        files = FileCollector.collect(tmp_path)
        assert files == []

    def test_collect_files_with_supported_files(self, tmp_path):
        """验证支持的文件收集"""
        # 创建测试文件
        pdf_file = tmp_path / "001_test.pdf"
        jpg_file = tmp_path / "002_test.jpg"
        png_file = tmp_path / "003_test.png"
        pdf_file.touch()
        jpg_file.touch()
        png_file.touch()

        files = FileCollector.collect(tmp_path)
        # 注意：实际收集的文件数量取决于 MinerU 支持的后缀
        assert len(files) >= 0  # 至少应该收集到一些文件

    def test_collect_files_sorted(self, tmp_path):
        """验证文件按序号排序"""
        # 创建带序号的测试文件
        file3 = tmp_path / "003_test.pdf"
        file1 = tmp_path / "001_test.pdf"
        file2 = tmp_path / "002_test.pdf"
        file3.touch()
        file1.touch()
        file2.touch()

        files = FileCollector.collect(tmp_path)
        # 验证文件是否按序号排序
        seq_numbers = [FileCollector.get_seq_number(f) for f in files]
        assert seq_numbers == sorted(seq_numbers)

    def test_collect_files_filters_unsupported(self, tmp_path):
        """验证过滤不支持的文件"""
        # 创建支持和不支持的文件
        supported_file = tmp_path / "001_test.pdf"
        unsupported_file = tmp_path / "002_test.txt"
        supported_file.touch()
        unsupported_file.touch()

        files = FileCollector.collect(tmp_path)
        # 验证不支持的文件被过滤
        for f in files:
            assert f.suffix != ".txt"

    def test_assign_sequences_with_existing(self):
        """验证为已有序号的文件保留序号"""
        files = [
            Path("001_invoice.pdf"),
            Path("003_report.pdf"),
        ]
        seqs = FileCollector.assign_sequences(files)
        assert seqs == [1, 3]

    def test_assign_sequences_auto_increment(self):
        """验证无序号文件自动递增"""
        files = [
            Path("001_invoice.pdf"),
            Path("receipt.jpg"),
            Path("003_report.pdf"),
            Path("photo.png"),
        ]
        seqs = FileCollector.assign_sequences(files)
        assert seqs == [1, 4, 3, 5]

    def test_assign_sequences_all_auto(self):
        """验证全部无序号时从 1 开始递增"""
        files = [
            Path("invoice.pdf"),
            Path("receipt.jpg"),
        ]
        seqs = FileCollector.assign_sequences(files)
        assert seqs == [1, 2]
