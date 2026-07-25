"""输入文件收集 - 按序号前缀排序、zip 自动解压"""
import re
import zipfile
from pathlib import Path

from loguru import logger

from mineru.cli.common import image_suffixes, office_suffixes, pdf_suffixes
from mineru.utils.guess_suffix_or_lang import guess_suffix_by_path

SUPPORTED_SUFFIXES = set(pdf_suffixes + image_suffixes + office_suffixes + [".xml"])
SEQ_PATTERN = re.compile(r"^(\d{3})_")


class FileCollector:
    @staticmethod
    def get_seq_number(file_path: Path) -> int:
        m = SEQ_PATTERN.match(file_path.name)
        return int(m.group(1)) if m else 0

    @staticmethod
    def assign_sequences(files: list[Path]) -> list[int]:
        """为文件列表分配序号，无序号文件自动递增。"""
        seqs = [FileCollector.get_seq_number(f) for f in files]
        max_seq = max(s for s in seqs) if seqs else 0
        result = []
        for s in seqs:
            if s == 0:
                max_seq += 1
                result.append(max_seq)
            else:
                result.append(s)
        return result

    @staticmethod
    def extract_zips(input_dir: Path) -> None:
        """解压 input 目录下的 zip 文件，统一 UTF-8 编码"""
        for zf in sorted(input_dir.glob("*.zip")):
            logger.info(f"Extracting zip: {zf.name}")
            with zipfile.ZipFile(zf) as archive:
                for info in archive.infolist():
                    # 统一 UTF-8 编码处理文件名
                    target = input_dir / info.filename
                    archive.extract(info, input_dir)
            zf.unlink()
            logger.info(f"Extracted and removed: {zf.name}")

    @classmethod
    def collect(cls, input_dir: Path) -> list[Path]:
        cls.extract_zips(input_dir)
        return sorted(
            (p for p in input_dir.rglob("*")
             if p.is_file() and (guess_suffix_by_path(p) in SUPPORTED_SUFFIXES
                                or p.suffix.lower() == ".xml")),
            key=lambda p: cls.get_seq_number(p) or 999,
        )
