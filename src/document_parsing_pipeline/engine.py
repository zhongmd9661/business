"""MinerU 解析引擎 - 通过 LocalAPIServer 调用"""
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

os.environ["MINERU_MODEL_SOURCE"] = "local"

from mineru.cli import api_client as _api_client
from mineru.cli.common import image_suffixes, office_suffixes, pdf_suffixes
from mineru.utils.guess_suffix_or_lang import guess_suffix_by_path
from mineru.utils.config_reader import get_local_models_dir
from mineru.utils.enum_class import ModelPath

import httpx
from loguru import logger

from ..batch_processing import FileCollector
from ..output_visualization import OutputOrganizer

SUPPORTED_SUFFIXES = set(pdf_suffixes + image_suffixes + office_suffixes)


@dataclass
class ParseOptions:
    backend: str = "pipeline"
    lang: list[str] = ("ch",)
    method: str = "auto"
    formula: bool = True
    table: bool = True
    image_analysis: bool = True
    return_images: bool = False
    return_md: bool = True
    return_json: bool = True


@dataclass
class ParseResult:
    file_path: Path
    seq: int
    output_dir: Path
    success: bool
    elapsed: float = 0.0
    error: Optional[str] = None


_REQUIRED_MODEL_PATHS = [
    ModelPath.pp_doclayout_v2,
    ModelPath.unimernet_small,
    ModelPath.pp_formulanet_plus_m,
    ModelPath.pytorch_paddle,
    ModelPath.slanet_plus,
    ModelPath.unet_structure,
    ModelPath.paddle_table_cls,
]


class MinerUEngine:
    """MinerU 解析引擎，管理 LocalAPIServer 生命周期和文件解析"""

    def __init__(self, options: Optional[ParseOptions] = None):
        self.options = options or ParseOptions()
        self._local_server = None
        self._http_client = None

    @staticmethod
    def _check_models_available() -> bool:
        models_dir = get_local_models_dir()
        if not models_dir or "pipeline" not in models_dir:
            logger.warning("MinerU 模型路径未配置")
            return False

        pipeline_root = models_dir["pipeline"]
        missing = [p for p in _REQUIRED_MODEL_PATHS if not Path(pipeline_root, p).exists()]
        if missing:
            logger.warning(f"以下模型未找到: {', '.join(missing)}")
            return False
        return True

    def _build_form_data(self):
        return _api_client.build_parse_request_form_data(
            lang_list=self.options.lang,
            backend=self.options.backend,
            parse_method=self.options.method,
            formula_enable=self.options.formula,
            table_enable=self.options.table,
            image_analysis=self.options.image_analysis,
            server_url=None,
            start_page_id=0,
            end_page_id=None,
            return_md=self.options.return_md,
            return_middle_json=self.options.return_json,
            return_model_output=False,
            return_content_list=False,
            return_images=self.options.return_images,
            response_format_zip=True,
            return_original_file=False,
        )

    async def start(self):
        if not self._check_models_available():
            logger.error(
                "MinerU 模型未就绪。请先运行以下命令下载模型：\n"
                "  mineru-models-download -s modelscope -m pipeline\n\n"
                "下载完成后模型将保存在本地缓存目录，后续运行不会重复下载。"
            )
            raise RuntimeError("MinerU 模型未就绪，请先下载模型")

        self._local_server = _api_client.LocalAPIServer()
        base_url = self._local_server.start()
        logger.info(f"Started local mineru-api: {base_url}")
        self._http_client = httpx.AsyncClient(
            timeout=_api_client.build_http_timeout(),
            follow_redirects=True,
        )
        await _api_client.wait_for_local_api_ready(self._http_client, self._local_server)

    async def stop(self):
        if self._local_server:
            self._local_server.stop()
        if self._http_client:
            await self._http_client.aclose()

    async def parse_file(self, file_path: Path, output_dir: Path, seq: int, batch_summary: str = None) -> ParseResult:
        start_time = datetime.now()
        form_data = self._build_form_data()
        upload_assets = [_api_client.UploadAsset(path=file_path, upload_name=file_path.name)]

        try:
            submit_response = await _api_client.submit_parse_task(
                base_url=self._local_server.base_url,
                upload_assets=upload_assets,
                form_data=form_data,
            )

            await _api_client.wait_for_task_result(
                client=self._http_client,
                submit_response=submit_response,
                task_label=file_path.name,
            )

            result_zip_path = await _api_client.download_result_zip(
                client=self._http_client,
                submit_response=submit_response,
                task_label=file_path.name,
            )

            raw_dir = OutputOrganizer.extract(result_zip_path, output_dir / "_raw")
            out_dir = OutputOrganizer.reorganize(raw_dir, output_dir, seq, file_path.stem, batch_summary)

            elapsed = (datetime.now() - start_time).total_seconds()
            return ParseResult(
                file_path=file_path,
                seq=seq,
                output_dir=out_dir,
                success=True,
                elapsed=elapsed,
            )
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"Failed to parse {file_path.name}: {e}")
            return ParseResult(
                file_path=file_path,
                seq=seq,
                output_dir=output_dir / f"{seq}_{file_path.stem}",
                success=False,
                elapsed=elapsed,
                error=str(e),
            )
