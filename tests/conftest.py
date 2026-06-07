"""Pytest 配置文件"""
import sys
from pathlib import Path

import pytest
from loguru import logger

# 添加项目根目录到 Python 路径，以便导入 src 模块
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def setup_loguru_caplog(caplog):
    """让 loguru 日志能被 caplog 捕获"""
    import logging
    # 移除默认控制台 handler，添加 caplog handler
    handler_id = logger.add(
        caplog.handler,
        format="{message}",
        level="DEBUG",
    )
    yield
    logger.remove(handler_id)
