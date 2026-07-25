"""Webhook 告警通知器"""
from __future__ import annotations

import json
import logging
from datetime import datetime

import requests

from .models import Finding

logger = logging.getLogger(__name__)


class WebhookNotifier:
    """发现高风险问题时通过 Webhook 发送告警通知。"""

    def __init__(self, url: str):
        self._url = url

    def notify(self, findings: list[Finding], filename: str) -> bool:
        """仅对高风险问题发送 POST 请求。

        Args:
            findings: 审核发现列表
            filename: 来源文档名

        Returns:
            True 表示发送成功，False 表示跳过或失败
        """
        high_risks = [f for f in findings if f.level == "高"]
        if not high_risks:
            return False

        payload = {
            "filename": filename,
            "timestamp": datetime.now().isoformat(),
            "count": len(high_risks),
            "findings": [
                {
                    "category": f.category.value,
                    "rule": f.rule,
                    "clause": f.clause,
                    "message": f.message,
                    "detail": f.detail,
                }
                for f in high_risks
            ],
        }

        try:
            resp = requests.post(
                self._url,
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            logger.info(f"Webhook sent for {filename}: {len(high_risks)} high-risk finding(s)")
            return True
        except Exception as e:
            logger.error(f"Webhook failed for {filename}: {e}")
            return False
