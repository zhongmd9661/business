"""企查查截图分析 API — 支持 RapidOCR（默认）和 VLM 两种识别方式"""
import asyncio
import base64
import io
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from loguru import logger
from PIL import Image

router = APIRouter()


@router.post("/qichacha/analyze")
async def analyze_qichacha(
    file: UploadFile = File(...),
    method: str = Form("ocr"),  # "ocr" (default) or "vlm"
    device: str = Form("auto"),  # "auto", "cpu", "gpu"
):
    """
    上传企查查截图，分析企业经营状态。
    method: "ocr" = RapidOCR（默认，快）; "vlm" = 视觉大模型（慢，准确）
    device: "auto" = 自动检测（默认）; "cpu" = 强制 CPU; "gpu" = 强制 GPU
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

    # Route to appropriate engine
    if method == "vlm":
        # VLM: encode to base64
        img_bytes = io.BytesIO()
        img = Image.open(io.BytesIO(content))
        img.save(img_bytes, format="PNG")
        b64_data = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
        result = _analyze_with_vision(b64_data, "png")
    else:
        # RapidOCR (default)
        img_reopened = Image.open(io.BytesIO(content))
        result = _analyze_with_ocr(img_reopened, device=device)

    return {
        "success": True,
        "analyzed_at": datetime.now().isoformat(),
        "_method": method,
        **result,
    }


def _analyze_with_vision(image_b64: str, image_format: str = "png") -> dict:
    """使用视觉大模型分析企查查截图"""
    import os
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
   - 以下状态视为**异常**：注销、吊销、经营异常、严重违法、停业、歇业、迁出、撤销、被执行人、失信被执行人
   - 以下状态视为**正常**：存续、在业、开业
   - 无法确定时视为异常（安全优先）
   - 注意：如果页面显示"被执行人"或"失信"标签，也视为异常
6. **recommendation**: 处理建议（如果异常，说明原因并建议不提交；如果正常，建议可以提交）
7. **markdown_text**: 将截图中识别到的**所有文字**整理为 Markdown 格式。要求：
   - 保持页面结构（企业信息、联系方式、风险信息、动态等分区）
   - 使用标题、列表、表格等 Markdown 语法组织内容
   - 不要遗漏重要字段，方便人工与原图对比

**重要**：请只返回JSON，不要包含markdown代码块标记，格式如下：
{"company_name":"xxx","business_status":"xxx","risk_count":0,"risk_summary":"xxx","is_abnormal":false,"recommendation":"xxx","markdown_text":"# 企业名称\\n\\n基本信息\\n- 统一社会信用代码：xxx\\n..."}"""

    try:
        import httpx
        url = f"{base_url.rstrip('/')}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }
        body = {
            "model": model,
            "max_tokens": 2048,
            "system": system_prompt,
            "messages": [
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
            "temperature": 0.1,
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, json=body, headers=headers)

        if response.status_code != 200:
            raise RuntimeError(f"LLM API 返回错误 (HTTP {response.status_code}): {response.text[:500]}")

        data_resp = response.json()
        content_blocks = data_resp.get("content", [])
        content = ""
        for block in content_blocks:
            if block.get("type") == "text":
                content = block.get("text", "")
                break

        # Clean up markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        # Try to find JSON object in the response
        json_start = content.find('{')
        json_end = content.rfind('}')
        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end + 1]
        else:
            json_str = content.strip()

        data = json.loads(json_str)
        return data

    except Exception as e:
        import traceback
        logger.error(f"企查查截图识别失败: {e}\n{traceback.format_exc()}")
        # Return a safe fallback — don't block if vision engine fails
        return {
            "company_name": "",
            "business_status": "无法识别",
            "risk_count": 0,
            "risk_summary": f"视觉识别引擎暂时不可用: {str(e)}",
            "is_abnormal": False,
            "recommendation": "分析服务暂时不可用，暂不限制提交。建议人工核对企业经营状态。",
            "markdown_text": "",
            "ocr_lines": [],
            "ocr_blocks": [],
            "img_width": 0,
            "img_height": 0,
            "_error": str(e)
        }


# ==================== OCR 识别引擎（RapidOCR / PaddleOCR）====================
# 共享 OCR 引擎实例从 router_ocr.py 导入（避免重复初始化）

# 异常状态关键词
ABNORMAL_STATUSES = {
    "注销", "吊销", "经营异常", "严重违法", "停业", "歇业",
    "迁出", "撤销", "被执行人", "失信被执行人", "异常经营",
    "列入经营异常名录", "严重违法失信企业名单",
}
NORMAL_STATUSES = {"存续", "在业", "开业"}


def _get_ocr(device: str = "auto"):
    """获取 OCR 单例 — 委托给 router_ocr.py 的共享实例"""
    from .router_ocr import _get_ocr as _shared_get_ocr
    return _shared_get_ocr(device)


def _ocr_image(img: "Image.Image", device: str = "auto") -> str:
    """使用 RapidOCR 识别图片，返回拼接后的纯文本"""
    import numpy as np

    ocr = _get_ocr(device=device)
    result, _ = ocr(np.asarray(img))

    if not result:
        return ""

    result_sorted = sorted(result, key=lambda x: x[0][0][1])
    lines = []
    for word_info in result_sorted:
        text = word_info[1]
        lines.append(text)
    return "\n".join(lines)


def _ocr_image_with_boxes(img: "Image.Image", device: str = "auto") -> list:
    """使用 RapidOCR 识别图片，返回带坐标信息的文字块列表"""
    import numpy as np

    ocr = _get_ocr(device=device)
    result, _ = ocr(np.asarray(img))

    if not result:
        return []

    blocks = []
    for word_info in result:
        box_points = word_info[0]
        text_and_score = word_info[1]
        score = word_info[2] if len(word_info) > 2 else 1.0

        xs = [p[0] for p in box_points]
        ys = [p[1] for p in box_points]
        x = int(min(xs))
        y = int(min(ys))
        w = int(max(xs)) - x
        h = int(max(ys)) - y

        blocks.append({
            "text": text_and_score,
            "x": x,
            "y": y,
            "w": max(w, 1),
            "h": max(h, 1),
            "score": float(score) if score else 1.0,
        })

    return blocks


def _analyze_with_ocr(img: "Image.Image", device: str = "auto") -> dict:
    """使用 RapidOCR + 规则匹配分析企查查截图"""
    import numpy as np

    try:
        # 0. 获取图片尺寸（用于前端缩放定位）
        img_w, img_h = img.size

        # 1. OCR 提取全部文字
        text = _ocr_image(img, device=device)

        # 1b. 获取带坐标的 OCR 块
        ocr_blocks = _ocr_image_with_boxes(img, device=device)

        # 2. 按行拆分
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        full_text = "\n".join(lines)

        # 3. 提取企业名称
        company_name = ""
        # 企查查截图通常第一行或前几行就是企业名称
        for line in lines[:10]:
            # 匹配 "有限公司" / "股份有限公司" / "集团" / "中心" / "局" / "委员会" 等
            if re.search(r"(有限|集团|股份|中心|局|委员会|办事处|分公司|事务所|学校|医院|协会|商会|公司|厂|所)", line):
                # 去掉可能的编号/前缀
                cleaned = re.sub(r"^[\s\d、①②③④⑤⑥⑦⑧⑨⑩\-•·]*", "", line)
                company_name = cleaned
                break

        # 4. 提取经营状态
        business_status = "无法识别"
        for line in lines:
            # 匹配 "经营状态：存续" 或 "状态  存续" 等模式
            match = re.search(r"经营(?:状态|情况)\s*[：:]\s*(.+)", line)
            if match:
                business_status = match.group(1).strip()
                break
        # 如果上面没匹配到，尝试关键词搜索
        if business_status == "无法识别":
            for line in lines:
                for status in ABNORMAL_STATUSES | NORMAL_STATUSES:
                    if status in line:
                        business_status = status
                        break
                if business_status != "无法识别":
                    break

        # 5. 判断是否异常
        is_abnormal = False
        if business_status != "无法识别":
            for ab in ABNORMAL_STATUSES:
                if ab in business_status:
                    is_abnormal = True
                    break
        # 额外检查全文是否有失信/被执行人标签
        if not is_abnormal:
            if "失信被执行人" in full_text or "被执行人" in full_text:
                is_abnormal = True
                if business_status == "无法识别":
                    business_status = "被执行人"

        # 如果完全识别不到，安全优先视为异常
        if business_status == "无法识别":
            is_abnormal = True

        # 6. 提取风险数量
        risk_count = 0
        risk_match = re.search(r"自身风险\s*[：:]\s*(\d+)", full_text)
        if risk_match:
            risk_count = int(risk_match.group(1))
        # 也试试 "涉及风险" / "提示信息"
        if risk_count == 0:
            risk_match2 = re.search(r"(?:涉及|提示)风险\s*[：:]\s*(\d+)", full_text)
            if risk_match2:
                risk_count = int(risk_match2.group(1))

        # 7. 生成风险摘要
        risk_summary = ""
        risk_keywords = ["风险", "异常", "处罚", "冻结", "失信", "被执行人",
                         "严重违法", "警告", "告警", "诉讼", "仲裁"]
        risk_lines = [l for l in lines if any(kw in l for kw in risk_keywords)]
        if risk_lines:
            risk_summary = "；".join(risk_lines[:5])
        elif risk_count > 0:
            risk_summary = f"发现 {risk_count} 条风险信息"
        else:
            risk_summary = "未发现明显风险"

        # 8. 生成处理建议
        if is_abnormal:
            recommendation = (
                f"⚠️ 该企业经营状态为「{business_status}」，属于异常状态。"
                "建议不提交此接待记录，或请人工进一步核实。"
            )
        else:
            recommendation = (
                f"✅ 该企业经营状态为「{business_status}」，经营状态正常，"
                "可以提交此接待记录。"
            )

        # 9. 生成 Markdown 文字（OCR 结果按行整理）— 保留兼容
        markdown_text = f"# {company_name or '企查查截图'}\n\n"
        markdown_text += "## 识别结果\n\n"
        markdown_text += f"- **企业名称**：{company_name or '未识别'}\n"
        markdown_text += f"- **经营状态**：{business_status}\n"
        markdown_text += f"- **风险数量**：{risk_count}\n"
        markdown_text += f"- **风险提示**：{risk_summary}\n"
        markdown_text += f"\n---\n\n## 原始文字\n\n"
        markdown_text += "\n".join(f"{line}" for line in lines)

        return {
            "company_name": company_name,
            "business_status": business_status,
            "risk_count": risk_count,
            "risk_summary": risk_summary,
            "is_abnormal": is_abnormal,
            "recommendation": recommendation,
            "markdown_text": markdown_text,
            "ocr_lines": lines,  # 原始 OCR 逐行文字，兼容旧前端
            "ocr_blocks": ocr_blocks,  # 带坐标的 OCR 块，用于前端绝对定位渲染
            "img_width": img_w,
            "img_height": img_h,
        }

    except ImportError:
        return {
            "company_name": "",
            "business_status": "无法识别",
            "risk_count": 0,
            "risk_summary": "OCR 引擎未安装。请运行: pip install rapidocr-onnxruntime",
            "is_abnormal": False,
            "recommendation": "OCR 引擎未安装，请安装后重试或切换到 VLM 识别。",
            "markdown_text": "",
            "ocr_lines": [],
            "ocr_blocks": [],
            "img_width": 0,
            "img_height": 0,
            "_error": "rapidocr-onnxruntime not installed"
        }
    except Exception as e:
        import traceback
        logger.error(f"OCR 识别失败: {e}\n{traceback.format_exc()}")
        return {
            "company_name": "",
            "business_status": "无法识别",
            "risk_count": 0,
            "risk_summary": f"OCR 识别失败: {str(e)}",
            "is_abnormal": False,
            "recommendation": "OCR 识别失败，请尝试切换到 VLM 识别或重新上传截图。",
            "markdown_text": "",
            "ocr_blocks": [],
            "img_width": img_w if 'img_w' in dir() else 0,
            "img_height": img_h if 'img_h' in dir() else 0,
            "_error": str(e)
        }


# ==================== QCC 浏览器自动查询 ====================

@router.post("/qcc/query")
async def query_qcc_company(body: dict):
    """
    通过浏览器自动查询企查查获取企业信息。
    请求: POST /api/qcc/query  body: {"company_name": "腾讯"}
    响应: {"success": true, "companies": [...]}
    注意: 需要先运行 start_browser.py 启动 Edge 浏览器（CDP 端口 9223）
    """
    company_name = body.get("company_name", "").strip()
    if not company_name:
        raise HTTPException(400, "请输入企业名称")

    try:
        from qcc_scraper.browser import BrowserManager
        from qcc_scraper.login_checker import check_and_login
        from qcc_scraper.searcher import Searcher
        from qcc_scraper.collector import Collector
        from qcc_scraper.config import QCC_URL

        def _run_scraper():
            browser = None
            try:
                browser = BrowserManager().launch()
                page = browser.navigate_to(QCC_URL)

                if not check_and_login(page):
                    raise RuntimeError("登录失败，请在浏览器中完成登录后重试")

                browser.close_popup()

                searcher = Searcher(page)
                searcher.search(company_name)

                browser.close_popup()

                collector = Collector(page)
                companies = collector.extract_company_list()
                return companies

            finally:
                if browser:
                    browser.close()

        # 在后台线程运行（Playwright 是同步 API，避免阻塞 event loop）
        companies = await asyncio.wait_for(
            asyncio.to_thread(_run_scraper),
            timeout=60.0
        )

        logger.info("QCC 查询成功: {} -> {} 条结果", company_name, len(companies))

        return {
            "success": True,
            "query": company_name,
            "count": len(companies),
            "companies": companies,
        }

    except asyncio.TimeoutError:
        logger.error("QCC 查询超时: {}", company_name)
        return {
            "success": False,
            "error": "查询超时（60秒）。请检查网络连接或稍后重试。",
            "companies": [],
        }
    except RuntimeError as e:
        msg = str(e)
        if "未检测到浏览器运行" in msg or "CDP" in msg:
            return {
                "success": False,
                "error": "浏览器未启动。请先运行 start_browser.py 启动 Edge 浏览器。",
                "companies": [],
            }
        return {
            "success": False,
            "error": msg,
            "companies": [],
        }
    except Exception as e:
        import traceback
        logger.error(f"QCC 查询失败: {e}\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": f"查询失败: {str(e)}",
            "companies": [],
        }
