"""Vision LLM 识别引擎 - 将图像直接转换为带有语义结构的碎片数据
实现目标：提取表头、行数据及用于拼接的语义指纹，忽略水印干扰。
"""
from __future__ import annotations

import base64
import os
import pathlib
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from anthropic import Anthropic

@dataclass
class VisionFragment:
    """单张图片识别出的语义碎片"""
    image_id: str
    headers: List[str]  # 识别出的表头清单
    rows: List[Dict[str, Any]]  # 结构化行数据
    fingerprints: List[str]  # 每行的唯一指纹 (用于 Y 轴对齐)
    raw_text: str # 备份文本

class LlmVisionEngine:
    """使用视觉大模型直接识别图片并提取结构化碎片"""

    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        self.base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL", "http://192.168.231.1:1235")
        self.api_key = api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "lmstudio")
        self.model = model or os.environ.get("LLM_MODEL", "qwen/qwen3.6-27b")
        self._client: Optional[Anthropic] = None

    def start(self):
        self._client = Anthropic(base_url=self.base_url, api_key=self.api_key)

    def stop(self):
        self._client = None

    def _encode_image(self, image_path: pathlib.Path) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def parse_image(self, image_path: pathlib.Path) -> VisionFragment:
        """识别单张图片并提取结构化碎片"""
        if self._client is None:
            raise RuntimeError("请先调用 start() 初始化客户端")

        image_base64 = self._encode_image(image_path)

        # 针对仿真手机报表的 System Prompt
        system_prompt = (
            "你是一个专业的报表识别专家。你的任务是将图片中的表格数据还原为结构化JSON。"
            "\n\n重要要求："
            "\n1. **忽略水印**：图片中可能存在透明或半透明的水印，请完全忽略它们，只提取业务数据。"
            "\n2. **保持原整**：不要总结、不要省略，完整提取所有可见的行和列。"
            "\n3. **识别表头**：准确识别表格的所有列名。"
            "\n4. **生成指纹**：为每一行生成一个唯一的语义指纹（通常由序号+日期+项目名称组成），用于后续拼接。"
            "\n5. **输出格式**：必须返回纯JSON，包含 'headers', 'rows' (每项含列名:值), 和 'fingerprints' 列表。"
        )

        response = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg", # 简化处理，实际应根据后缀判断
                                "data": image_base64,
                            },
                        },
                        {"type": "text", "text": "请识别此图中的报表数据。"},
                    ],
                }
            ],
            temperature=0.1,
        )

        content = response.content[0].text
        # 简单清洗 JSON 标记 (实际应使用更鲁棒的解析逻辑)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        import json
        data = json.loads(content)

        return VisionFragment(
            image_id=image_path.name,
            headers=data.get("headers", []),
            rows=data.get("rows", []),
            fingerprints=data.get("fingerprints", []),
            raw_text=content
        )
