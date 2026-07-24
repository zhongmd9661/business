"""企查查截图分析 API — 通过视觉模型识别企业经营状态"""
import base64
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from PIL import Image

router = APIRouter()


@router.post("/qichacha/analyze")
async def analyze_qichacha(file: UploadFile = File(...)):
    """
    上传企查查截图，分析企业经营状态。
    返回：公司名称、经营状态、风险提示、是否允许提交
    """
    # Validate file type
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"不支持的图片格式: {ext}。请上传 JPG/PNG 格式")

    # Read and validate image
    content = await file.read()
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(400, "图片文件损坏，请重新上传")

    # Encode to base64
    img_bytes = io.BytesIO()
    img = Image.open(io.BytesIO(content))
    img.save(img_bytes, format="PNG")
    b64_data = base64.b64encode(img_bytes.getvalue()).decode("utf-8")

    # Call LLM Vision Engine
    result = _analyze_with_vision(b64_data, "png")

    return {
        "success": True,
        "analyzed_at": datetime.now().isoformat(),
        **result
    }


def _analyze_with_vision(image_b64: str, image_format: str = "png") -> dict:
    """使用视觉大模型分析企查查截图"""
    import os
    from anthropic import Anthropic

    base_url = os.environ.get("ANTHROPIC_BASE_URL", "http://192.168.231.1:1235")
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "lmstudio")
    model = os.environ.get("LLM_MODEL", "Qwen/Qwen3.6-27B")

    system_prompt = """你是一个专业的企业信息分析助手。你的任务是分析企查查网页截图，提取关键信息。

请分析这张企查查截图，提取以下信息：

1. **company_name**: 企业名称（从页面顶部提取）
2. **business_status**: 经营状态（如"存续"、"在业"、"注销"、"吊销"、"经营异常"、"严重违法"等）
3. **risk_count**: 自身风险数量（如果有显示）
4. **risk_summary**: 风险提示摘要（简要描述发现的風險信息）
5. **is_abnormal**: 经营状态是否异常（布尔值）
   - 以下状态视为**异常**：注销、吊销、经营异常、严重违法、停业、歇业、迁出、撤销
   - 以下状态视为**正常**：存续、在业、开业
   - 无法确定时视为异常（安全优先）
6. **recommendation**: 处理建议（如果异常，说明原因并建议不提交；如果正常，建议可以提交）

**重要**：请只返回JSON，不要包含markdown代码块标记，格式如下：
{"company_name":"xxx","business_status":"xxx","risk_count":0,"risk_summary":"xxx","is_abnormal":false,"recommendation":"xxx"}"""

    try:
        client = Anthropic(base_url=base_url, api_key=api_key)

        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": f"image/{image_format}",
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": "请分析这张企查查截图中的企业经营状态和风险信息。"},
                    ],
                }
            ],
            temperature=0.1,
        )

        content = response.content[0].text

        # Clean up markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
        return data

    except Exception as e:
        # Return a safe fallback — don't block if vision engine fails
        return {
            "company_name": "",
            "business_status": "无法识别",
            "risk_count": 0,
            "risk_summary": f"视觉识别引擎暂时不可用: {str(e)}",
            "is_abnormal": False,  # Don't block if analysis fails
            "recommendation": "分析服务暂时不可用，暂不限制提交。建议人工核对企业经营状态。",
            "_error": str(e)
        }
