"""申请单生成器 — 模板加载、编辑、校验、生成"""

import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Any

from ..standards_query import standards, query
from .form_fields import TEMPLATE_TO_FORM, READONLY_FIELDS, APPLICATION_NO_PREFIX, APPLICATION_NO_TEMPLATE


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class ApplicationForm:
    """业务招待申请单"""
    application_no: str = ""
    applicant: str = ""
    department: str = ""
    position: str = ""
    application_date: str = ""
    reception_type: str = ""
    reception_category: str = ""
    reason: str = ""
    guest_info: str = ""
    guest_count: int = 0
    date: str = ""
    time_period: str = ""
    venue: str = ""
    is_holiday: bool = False
    companion_list: str = ""
    companion_count: int = 0
    companion_limit_info: str = ""
    per_person_limit: str = ""
    per_person_actual: float = 0.0
    total_amount: float = 0.0
    accommodation: str = ""
    transport: str = ""
    alcohol: str = ""
    alcohol_detail: str = ""
    souvenir: str = ""
    souvenir_detail: str = ""
    pre_approval: str = ""
    approver: str = ""
    approval_opinion: str = ""
    attachment_notes: str = ""
    generated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# ---------------------------------------------------------------------------
# 校验结果
# ---------------------------------------------------------------------------

@dataclass
class ValidationReport:
    """校验报告"""
    passed: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_warning(self, msg: str):
        self.warnings.append(msg)
        if self.passed:
            self.passed = True  # warnings don't block

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.passed = False

    def to_dict(self) -> dict:
        return {"passed": self.passed, "warnings": self.warnings, "errors": self.errors}


# ---------------------------------------------------------------------------
# 生成器
# ---------------------------------------------------------------------------

class FormGenerator:
    """申请单生成器"""

    def __init__(self):
        self._seq_counter = 0

    # ---- 模板操作 ----

    def get_all_templates(self) -> list[dict]:
        """获取所有场景模板"""
        from ..standards_query import templates
        return templates.get_templates()

    def get_template(self, template_id: str) -> dict | None:
        """获取单个模板"""
        from ..standards_query import templates
        return templates.get_template_by_id(template_id)

    def load_template_to_form(self, template_id: str) -> ApplicationForm:
        """从模板加载数据到申请单（预填）"""
        tpl = self.get_template(template_id)
        if not tpl:
            return ApplicationForm()

        form = ApplicationForm()
        example = tpl.get("example", {})

        # 映射模板字段 → 申请单字段
        for tpl_key, form_key in TEMPLATE_TO_FORM.items():
            value = example.get(tpl_key, "")
            if form_key == "guest_count":
                form.guest_count = int(value) if isinstance(value, (int, str)) and value else 0
            elif form_key == "companion_count":
                # 从 "≤X人（规则）" 提取数字
                form.companion_count = self._extract_number(str(value)) if value else 0
            elif form_key == "per_person_limit":
                # 提取金额数字
                form.per_person_limit = self._extract_std(str(value)) if value else ""
            elif form_key == "total_amount":
                form.total_amount = self._extract_amount(str(value)) if value else 0.0
            elif form_key == "alcohol":
                # 标准化酒水字段
                form.alcohol = self._normalize_alcohol(str(value))
            else:
                setattr(form, form_key, str(value) if value else "")

        # 自动计算总金额
        if form.per_person_limit and form.guest_count > 0:
            form.total_amount = self._calc_total(form.per_person_limit, form.guest_count)

        # 自动计算陪同人数规定
        if form.guest_count > 0 and form.reception_type:
            comp_type = "外部" if form.reception_type != "内部业务招待" else "内部"
            comp = query.calculate_companion_limit(form.guest_count, comp_type)
            form.companion_limit_info = f"{comp['规则']}（依据：{comp['依据']}）"

        # 自动生成申请单号
        now = datetime.now()
        form.application_no = APPLICATION_NO_TEMPLATE.format(
            year=now.strftime("%Y"),
            month=now.strftime("%m"),
            day=now.strftime("%d"),
            seq=self._seq_counter,
        )
        self._seq_counter += 1
        form.generated_at = now.isoformat()

        return form

    # ---- 校验 ----

    def validate(self, form: ApplicationForm) -> ValidationReport:
        """校验申请单完整性与合规性"""
        report = ValidationReport()

        # 必填字段检查
        required_fields = [
            ("申请人", form.applicant),
            ("申请部门", form.department),
            ("职务/职级", form.position),
            ("申请日期", form.application_date),
            ("招待类型", form.reception_type),
            ("招待类别", form.reception_category),
            ("招待事由", form.reason),
            ("招待对象", form.guest_info),
            ("招待人数", str(form.guest_count)),
            ("招待日期", form.date),
            ("用餐时段", form.time_period),
            ("用餐地点", form.venue),
            ("是否节假日", "是" if form.is_holiday else "否"),
            ("陪同人员", form.companion_list),
            ("陪同人数", str(form.companion_count)),
            ("人均金额", str(form.per_person_actual)),
            ("酒水情况", form.alcohol),
            ("纪念品", form.souvenir),
            ("事前审批", form.pre_approval),
        ]

        for label, value in required_fields:
            if not value or str(value).strip() == "":
                report.add_error(f"必填字段「{label}」不能为空")

        # 酒水校验（内部招待/工作餐 不允许酒水，独立于标准查询）
        if form.alcohol != "无酒水":
            if form.reception_type in ("内部业务招待", "工作餐"):
                report.add_error("内部业务招待/工作餐不得上烟酒")
            else:
                # 对外招待：检查酒水标准
                std = self._lookup_standard(form.position, form.reception_type)
                if std:
                    alcohol_text = std.get("酒水标准", "")
                    baijiu_limit = self._parse_alcohol_limit(alcohol_text, "白酒")
                    red_wine_limit = self._parse_alcohol_limit(alcohol_text, "红酒")
                    if baijiu_limit > 0:
                        report.add_warning(
                            f"白酒标准 ≤{baijiu_limit}元/500ml，请确保酒水明细符合标准"
                        )
                    if red_wine_limit > 0:
                        report.add_warning(
                            f"红酒标准 ≤{red_wine_limit}元/750ml，请确保酒水明细符合标准"
                        )

        # 金额标准校验
        if form.reception_type and form.position and form.guest_count > 0 and form.per_person_actual > 0:
            std = self._lookup_standard(form.position, form.reception_type)
            if std:
                meal_text = std.get("用餐标准", "")
                meal_limit = self._parse_amount(meal_text)
                if form.per_person_actual > meal_limit and meal_limit > 0:
                    report.add_error(
                        f"人均金额 {form.per_person_actual}元 超过标准 {meal_limit}元/人·次"
                    )

                # 纪念品校验
                if form.souvenir == "有纪念品":
                    souvenir_text = std.get("纪念品", "")
                    if souvenir_text == "不得赠送":
                        report.add_error("该招待类型不得赠送纪念品")
                    else:
                        souvenir_limit = self._parse_amount(souvenir_text)
                        if souvenir_limit > 0 and form.per_person_actual > souvenir_limit:
                            report.add_error(f"纪念品金额超过标准 {souvenir_limit}元/人·次")

        # 陪同人数校验
        if form.reception_type and form.guest_count > 0:
            comp_type = "外部" if form.reception_type != "内部业务招待" else "内部"
            comp = query.calculate_companion_limit(form.guest_count, comp_type)
            if form.companion_count > comp["陪同人数上限"]:
                report.add_error(
                    f"陪同人数 {form.companion_count}人 超过上限 {comp['陪同人数上限']}人"
                )

        # 节假日报备检查
        if form.is_holiday:
            report.add_warning(
                "⚠️ 节假日招待需提前向办公室备案并向同级纪委报告，报备资料将作为报销支撑材料"
            )

        # 金额合理性检查
        if form.total_amount > 0 and form.per_person_actual > 0 and form.guest_count > 0:
            expected = form.per_person_actual * form.guest_count
            if abs(form.total_amount - expected) > expected * 0.1:  # 10% tolerance
                report.add_warning(
                    f"总金额与人均×人数不一致：{form.total_amount} vs {expected}元"
                )

        return report

    # ---- 生成 HTML 申请单 ----

    def generate_html(self, form: ApplicationForm) -> str:
        """生成可打印的 HTML 申请单"""
        validation = self.validate(form)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>业务招待申请单 - {form.applicant}</title>
<style>
@page {{ size: A4; margin: 15mm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: "SimSun", "STSong", serif;
    background: #f5f5f5;
    color: #1a1a1a;
    line-height: 1.5;
    padding: 20px;
}}
.form-container {{
    max-width: 794px;
    margin: 0 auto;
    background: white;
    padding: 40px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}}
.form-header {{
    text-align: center;
    border-bottom: 3px double #333;
    padding-bottom: 16px;
    margin-bottom: 24px;
}}
.form-header h1 {{
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 4px;
    margin-bottom: 8px;
}}
.form-header .subtitle {{
    font-size: 13px;
    color: #666;
}}
.form-header .no {{
    font-size: 14px;
    margin-top: 8px;
    color: #c00;
    font-weight: 600;
}}
.section {{
    margin-bottom: 20px;
}}
.section-title {{
    font-size: 15px;
    font-weight: 700;
    background: #f0f0f0;
    padding: 6px 12px;
    border-left: 4px solid #333;
    margin-bottom: 0;
}}
.field-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
    border: 1px solid #333;
    border-top: none;
}}
.field-row {{
    display: contents;
}}
.field-label {{
    background: #fafafa;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 600;
    border-right: 1px solid #ddd;
    border-bottom: 1px solid #ddd;
    color: #555;
    white-space: nowrap;
}}
.field-value {{
    padding: 8px 12px;
    font-size: 14px;
    border-bottom: 1px solid #ddd;
    min-height: 36px;
}}
.field-value.highlight {{
    color: #c00;
    font-weight: 600;
}}
.field-value.warning {{
    color: #d97706;
    background: #fffbeb;
}}
.field-value.error {{
    color: #dc2626;
    background: #fef2f2;
}}
.field-full {{
    grid-column: 1 / -1;
}}
.field-full .field-label,
.field-full .field-value {{
    border-right: none;
}}
.validation-box {{
    margin-top: 20px;
    padding: 14px 16px;
    border-radius: 6px;
    font-size: 13px;
}}
.validation-box.pass {{
    background: #f0fdf4;
    border: 1px solid #86efac;
    color: #166534;
}}
.validation-box.warn {{
    background: #fffbeb;
    border: 1px solid #fde68a;
    color: #92400e;
}}
.validation-box.fail {{
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #991b1b;
}}
.validation-box h3 {{
    font-size: 14px;
    margin-bottom: 8px;
}}
.validation-box ul {{
    margin-left: 18px;
}}
.validation-box li {{
    margin: 4px 0;
}}
.signature-area {{
    margin-top: 30px;
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 20px;
    padding-top: 20px;
    border-top: 1px dashed #ccc;
}}
.signature-block {{
    text-align: center;
}}
.signature-block .label {{
    font-size: 13px;
    color: #666;
    margin-bottom: 40px;
}}
.signature-block .line {{
    border-bottom: 1px solid #333;
    margin: 0 10px 4px;
}}
@media print {{
    body {{ background: white; padding: 0; }}
    .form-container {{ box-shadow: none; padding: 0; }}
    .no-print {{ display: none; }}
}}
.btn-print {{
    position: fixed;
    bottom: 20px;
    right: 20px;
    padding: 12px 24px;
    background: #1a56db;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    z-index: 100;
}}
.btn-print:hover {{ background: #1749b8; }}
</style>
</head>
<body>
<div class="form-container">
    <div class="form-header">
        <h1>业务招待申请单</h1>
        <p class="subtitle">依据《清远分公司业务招待费管理办法（V9.0）》</p>
        <p class="no">申请单号：{form.application_no}</p>
    </div>

    <div class="no-print" style="text-align:right;margin-bottom:16px;">
        <button onclick="window.print()" style="padding:8px 20px;background:#1a56db;color:white;border:none;border-radius:6px;cursor:pointer;font-size:13px;">
            🖨️ 打印申请单
        </button>
    </div>

    <div class="section">
        <div class="section-title">📋 基本信息</div>
        <div class="field-grid">
            <div class="field-row">
                <div class="field-label">申请人</div>
                <div class="field-value">{form.applicant}</div>
            </div>
            <div class="field-row">
                <div class="field-label">申请部门</div>
                <div class="field-value">{form.department}</div>
            </div>
            <div class="field-row">
                <div class="field-label">职务/职级</div>
                <div class="field-value">{form.position}</div>
            </div>
            <div class="field-row">
                <div class="field-label">申请日期</div>
                <div class="field-value">{form.application_date}</div>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">🍽️ 招待信息</div>
        <div class="field-grid">
            <div class="field-row">
                <div class="field-label">招待类型</div>
                <div class="field-value highlight">{form.reception_type}</div>
            </div>
            <div class="field-row">
                <div class="field-label">招待类别</div>
                <div class="field-value">{form.reception_category}</div>
            </div>
            <div class="field-row field-full">
                <div class="field-label">招待事由</div>
                <div class="field-value">{form.reason}</div>
            </div>
            <div class="field-row">
                <div class="field-label">招待对象</div>
                <div class="field-value">{form.guest_info}</div>
            </div>
            <div class="field-row">
                <div class="field-label">招待人数</div>
                <div class="field-value highlight">{form.guest_count}人</div>
            </div>
            <div class="field-row">
                <div class="field-label">招待日期</div>
                <div class="field-value">{form.date}</div>
            </div>
            <div class="field-row">
                <div class="field-label">用餐时段</div>
                <div class="field-value">{form.time_period}</div>
            </div>
            <div class="field-row field-full">
                <div class="field-label">用餐地点</div>
                <div class="field-value">{form.venue}</div>
            </div>
            <div class="field-row">
                <div class="field-label">是否节假日</div>
                <div class="field-value {'warning' if form.is_holiday else ''}">{'是' if form.is_holiday else '否'}</div>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">👥 陪同人员</div>
        <div class="field-grid">
            <div class="field-row field-full">
                <div class="field-label">陪同人员</div>
                <div class="field-value" style="white-space:pre-wrap;">{form.companion_list}</div>
            </div>
            <div class="field-row">
                <div class="field-label">陪同人数</div>
                <div class="field-value highlight">{form.companion_count}人</div>
            </div>
            <div class="field-row">
                <div class="field-label">陪同规定</div>
                <div class="field-value">{form.companion_limit_info}</div>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">💰 费用预算</div>
        <div class="field-grid">
            <div class="field-row">
                <div class="field-label">人均标准</div>
                <div class="field-value highlight">{form.per_person_limit}</div>
            </div>
            <div class="field-row">
                <div class="field-label">人均金额</div>
                <div class="field-value">{form.per_person_actual}元</div>
            </div>
            <div class="field-row">
                <div class="field-label">预计总金额</div>
                <div class="field-value highlight" style="font-size:18px;">{form.total_amount}元</div>
            </div>
            <div class="field-row">
                <div class="field-label">酒水情况</div>
                <div class="field-value">{form.alcohol}</div>
            </div>
            {'<div class="field-row field-full"><div class="field-label">酒水明细</div><div class="field-value">' + form.alcohol_detail + '</div></div>' if form.alcohol_detail else ''}
            <div class="field-row">
                <div class="field-label">纪念品</div>
                <div class="field-value">{form.souvenir}</div>
            </div>
            {'<div class="field-row field-full"><div class="field-label">纪念品明细</div><div class="field-value">' + form.souvenir_detail + '</div></div>' if form.souvenir_detail else ''}
            {'<div class="field-row field-full"><div class="field-label">住宿安排</div><div class="field-value" style="white-space:pre-wrap;">' + form.accommodation + '</div></div>' if form.accommodation else ''}
            {'<div class="field-row field-full"><div class="field-label">用车安排</div><div class="field-value" style="white-space:pre-wrap;">' + form.transport + '</div></div>' if form.transport else ''}
        </div>
    </div>

    <div class="section">
        <div class="section-title">✅ 审批信息</div>
        <div class="field-grid">
            <div class="field-row">
                <div class="field-label">事前审批</div>
                <div class="field-value highlight">{form.pre_approval}</div>
            </div>
            <div class="field-row">
                <div class="field-label">审批人</div>
                <div class="field-value">{form.approver}</div>
            </div>
            <div class="field-row field-full">
                <div class="field-label">审批意见</div>
                <div class="field-value">{form.approval_opinion}</div>
            </div>
            <div class="field-row field-full">
                <div class="field-label">附件说明</div>
                <div class="field-value">{form.attachment_notes}</div>
            </div>
        </div>
    </div>

    <div class="validation-box {'pass' if validation.passed else 'fail'}">
        <h3>📊 校验结果：{'✅ 通过' if validation.passed else '❌ 不通过'}</h3>
        {'<ul>' + ''.join(f'<li>{w}</li>' for w in validation.warnings) + '</ul>' if validation.warnings else ''}
        {'<ul>' + ''.join(f'<li style="color:#dc2626;">❌ {e}</li>' for e in validation.errors) + '</ul>' if validation.errors else ''}
        {'<p>所有必填字段已填写，金额标准符合要求。</p>' if validation.passed and not validation.warnings and not validation.errors else ''}
    </div>

    <div class="signature-area">
        <div class="signature-block">
            <div class="label">申请人签字</div>
            <div class="line"></div>
        </div>
        <div class="signature-block">
            <div class="label">部门负责人</div>
            <div class="line"></div>
        </div>
        <div class="signature-block">
            <div class="label">分管领导审批</div>
            <div class="line"></div>
        </div>
    </div>

    <div style="margin-top:24px;padding-top:12px;border-top:1px solid #eee;font-size:11px;color:#999;text-align:center;">
        <p>生成时间：{form.generated_at}</p>
        <p>依据：《中国移动广东公司清远分公司业务招待费管理办法（V9.0）》</p>
    </div>
</div>

<button class="btn-print no-print" onclick="window.print()">🖨️ 打印</button>
</body>
</html>"""

    # ---- 私有方法 ----

    def _lookup_standard(self, position: str, reception_type: str) -> dict | None:
        """查找对应标准"""
        if reception_type in ("商务招待", "外事招待"):
            category = "外事/商务"
        elif reception_type == "其他公务招待":
            category = "其他公务"
        else:
            return None

        for std in standards.EXTERNAL_STANDARDS:
            if std.personnel_level == position and std.reception_type == category:
                return std.to_dict()
        return None

    def _extract_number(self, text: str) -> int:
        """从文本中提取数字"""
        import re
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else 0

    def _extract_std(self, text: str) -> str:
        """提取标准描述"""
        if "≤" in text:
            return text
        return text

    def _extract_amount(self, text: str) -> float:
        """提取金额"""
        import re
        match = re.search(r'(\d+\.?\d*)', text)
        return float(match.group(1)) if match else 0.0

    def _parse_amount(self, text: str) -> float:
        """从格式化的金额文本中提取数字，如 '300元/人·次' -> 300.0"""
        import re
        match = re.search(r'(\d+\.?\d*)', str(text))
        return float(match.group(1)) if match else 0.0

    def _parse_alcohol_limit(self, text: str, kind: str) -> float:
        """从酒水标准文本中提取特定酒水的限额，如 '白酒≤300元/500ml, 红酒≤300元/750ml'"""
        import re
        pattern = rf'{kind}≤(\d+\.?\d*)元'
        match = re.search(pattern, str(text))
        return float(match.group(1)) if match else 0.0

    def _normalize_alcohol(self, text: str) -> str:
        """标准化酒水字段"""
        text = text.strip()
        if "不上" in text or "无" in text or "不得" in text:
            return "无酒水"
        if "白酒" in text and "红酒" in text:
            return "白酒+红酒"
        if "白酒" in text:
            return "白酒"
        if "红酒" in text:
            return "红酒"
        return "无酒水"

    def _calc_total(self, per_person: str, count: int) -> float:
        """计算总金额"""
        match = __import__('re').search(r'(\d+\.?\d*)', str(per_person))
        if match:
            return float(match.group(1)) * count
        return 0.0



