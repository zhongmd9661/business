"""审核规则管理 — 管理员 API

管理审核规则（非提取规则），即 run_review 中调用的 6 条校验规则。
规则存储在 audit_rules 表中，支持增删改查和启用/禁用。
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .auth import get_admin_user
from .models_db import AuditRule, AuditRuleHistory, User, ExtractionRule, get_db

router = APIRouter()


# ===================================================================
# 默认规则种子数据
# ===================================================================

DEFAULT_RULES = [
    {
        "category": "一致性校验",
        "rule_name": "金额一致性",
        "clause": "以发票小写金额为准，审批单、支付凭证、支付流水、报账单金额应与发票一致",
        "level": "高",
        "description": "核对发票金额与各单据金额是否一致，差异超过 0.01 元即标记为不通过",
        "check_expression": "amount_consistency",
        "source_document": "系统内置",
        "enabled": True,
    },
    {
        "category": "一致性校验",
        "rule_name": "日期一致性",
        "clause": "以审批单招待日期为基准，发票日期应≤招待日期，支付时间应≥招待日期",
        "level": "高",
        "description": "核对审批单、发票、支付凭证的日期逻辑关系",
        "check_expression": "date_consistency",
        "source_document": "系统内置",
        "enabled": True,
    },
    {
        "category": "合规性校验",
        "rule_name": "招待标准合规性",
        "clause": "人均费用和陪同人数应符合招待类型标准",
        "level": "高",
        "description": "工作餐≤60元，内部≤150元，其他公务≤200元，外事/商务≤400元；陪同人数按标准限制",
        "check_expression": "standard_compliance",
        "source_document": "系统内置",
        "enabled": True,
    },
    {
        "category": "经营风险",
        "rule_name": "单位经营状态",
        "clause": "招待单位应处于正常经营状态",
        "level": "提示",
        "description": "检查招待单位是否正常经营，异常状态需人工审核",
        "check_expression": "business_status",
        "source_document": "系统内置",
        "enabled": True,
    },
    {
        "category": "一致性校验",
        "rule_name": "支付凭证一致性",
        "clause": "支付凭证和支付流水的关键信息应一致",
        "level": "高",
        "description": "比对交易单号、金额、商户名称等关键信息",
        "check_expression": "payment_consistency",
        "source_document": "系统内置",
        "enabled": True,
    },
    {
        "category": "一致性校验",
        "rule_name": "活动函件日期",
        "clause": "活动函件日期与招待日期应相差在±7天内",
        "level": "中",
        "description": "核对活动函件中的交流时间与审批单招待日期是否匹配",
        "check_expression": "event_date",
        "source_document": "系统内置",
        "enabled": True,
    },
]


# ===================================================================
# CRUD API
# ===================================================================

@router.get("/admin/review-rules/categories")
def get_categories(db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取所有规则分类"""
    _seed_default_rules(db)
    categories = db.query(AuditRule.category).filter(AuditRule.enabled == True).distinct().all()
    return sorted(set(c[0] for c in categories))


@router.get("/admin/review-rules")
def list_review_rules(
    category: str = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """获取所有审核规则（可选按分类筛选）"""
    _seed_default_rules(db)
    q = db.query(AuditRule)
    if category:
        q = q.filter(AuditRule.category == category)
    rules = q.order_by(AuditRule.id).all()
    return [_rule_to_dict(r) for r in rules]


@router.get("/admin/review-rules/{rule_id}")
def get_review_rule(rule_id: int, db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取单条规则详情"""
    rule = db.query(AuditRule).filter(AuditRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, f"规则 ID {rule_id} 不存在")
    return _rule_to_dict(rule)


@router.post("/admin/review-rules")
def create_or_update_review_rule(
    data: dict,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """新增或更新审核规则
    Body: {"category": "...", "rule_name": "...", "clause": "...", "level": "...",
           "description": "...", "check_expression": "...", "enabled": true}
    """
    rule_name = data.get("rule_name")
    if not rule_name:
        raise HTTPException(400, "rule_name 必填")

    existing = db.query(AuditRule).filter(AuditRule.rule_name == rule_name).first()

    if existing:
        old_dict = _rule_to_dict(existing)
        for field in ("category", "clause", "level", "description", "check_expression",
                       "source_document", "enabled"):
            if field in data:
                setattr(existing, field, data[field])
        existing.updated_at = datetime.now().isoformat()
        db.commit()
        db.refresh(existing)
        _add_history(db, existing.id, "update",
                      json.dumps(old_dict, ensure_ascii=False),
                      json.dumps(_rule_to_dict(existing), ensure_ascii=False),
                      _admin.id)
        return _rule_to_dict(existing)
    else:
        rule = AuditRule(
            category=data.get("category", "自定义"),
            rule_name=rule_name,
            clause=data.get("clause", ""),
            level=data.get("level", "中"),
            description=data.get("description", ""),
            check_expression=data.get("check_expression", ""),
            source_document=data.get("source_document", "手动创建"),
            enabled=data.get("enabled", True),
            created_by=_admin.id,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return _rule_to_dict(rule)


@router.put("/admin/review-rules/{rule_id}")
def update_review_rule(
    rule_id: int,
    data: dict,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """更新审核规则（按 ID）"""
    rule = db.query(AuditRule).filter(AuditRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, f"规则 ID {rule_id} 不存在")

    old_dict = _rule_to_dict(rule)
    for field in ("category", "clause", "level", "description", "check_expression",
                   "source_document", "enabled"):
        if field in data:
            setattr(rule, field, data[field])
    rule.updated_at = datetime.now().isoformat()
    db.commit()
    db.refresh(rule)

    _add_history(db, rule.id, "update",
                  json.dumps(old_dict, ensure_ascii=False),
                  json.dumps(_rule_to_dict(rule), ensure_ascii=False),
                  _admin.id)
    return _rule_to_dict(rule)


@router.delete("/admin/review-rules/{rule_id}")
def delete_review_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """删除审核规则（软删除：禁用）"""
    rule = db.query(AuditRule).filter(AuditRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, f"规则 ID {rule_id} 不存在")

    old_dict = _rule_to_dict(rule)
    rule.enabled = False
    rule.updated_at = datetime.now().isoformat()
    db.commit()

    _add_history(db, rule.id, "disable",
                  json.dumps(old_dict, ensure_ascii=False), "disabled", _admin.id)
    return {"detail": "已禁用", "rule_id": rule_id}


@router.post("/admin/review-rules/{rule_id}/restore")
def restore_review_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """恢复（启用）已禁用的规则"""
    rule = db.query(AuditRule).filter(AuditRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, f"规则 ID {rule_id} 不存在")

    rule.enabled = True
    rule.updated_at = datetime.now().isoformat()
    db.commit()

    _add_history(db, rule.id, "enable", "disabled", "enabled", _admin.id)
    return _rule_to_dict(rule)


@router.get("/admin/review-rules/history/{rule_id}")
def get_rule_history(rule_id: int, db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取规则变更历史"""
    history = (
        db.query(AuditRuleHistory)
        .filter(AuditRuleHistory.rule_id == rule_id)
        .order_by(AuditRuleHistory.changed_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": h.id,
            "action": h.action,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "changed_by": h.changed_by,
            "changed_at": h.changed_at,
        }
        for h in history
    ]


# ===================================================================
# 工具函数
# ===================================================================

def _rule_to_dict(r: AuditRule) -> dict:
    """将数据库对象转为字典"""
    return {
        "id": r.id,
        "category": r.category,
        "rule_name": r.rule_name,
        "clause": r.clause,
        "level": r.level,
        "description": r.description or "",
        "check_expression": r.check_expression,
        "source_document": r.source_document or "",
        "enabled": r.enabled,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def _add_history(db: Session, rule_id: int, action: str, old_value: str, new_value: str, user_id: int):
    """记录规则变更历史"""
    h = AuditRuleHistory(
        rule_id=rule_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        changed_by=user_id,
        changed_at=datetime.now().isoformat(),
    )
    db.add(h)


def _seed_default_rules(db: Session):
    """初始化默认规则（首次调用时插入）"""
    existing = db.query(AuditRule).filter(
        AuditRule.check_expression == "amount_consistency"
    ).first()
    if existing:
        return  # 已有种子数据，跳过

    for rd in DEFAULT_RULES:
        rule = AuditRule(**{k: v for k, v in rd.items() if k != "enabled"})
        rule.enabled = rd.get("enabled", True)
        db.add(rule)
    db.commit()



# ===================================================================
# 槽位字段查询 — 供 UI 动态读取字段列表
# ===================================================================

@router.get("/admin/review-rules/slot-fields")
def get_slot_fields(db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取所有槽位及其定义的字段列表（从 extraction_rules 动态读取）"""
    rules = db.query(ExtractionRule).filter(ExtractionRule.enabled == True).all()
    result = {}
    for rule in rules:
        if rule.fields_json:
            try:
                fields = json.loads(rule.fields_json)
                field_names = [f.get("name", "") for f in fields if f.get("name")]
                result[rule.slot_name] = field_names
            except json.JSONDecodeError:
                pass
    return result


# ===================================================================
# 规则模板 — 系统预置常用规则，一键应用
# ===================================================================

from .service_audit import SLOTS

SLOT_NAMES_LIST = [s["name"] for s in SLOTS]

RULE_TEMPLATES = [
    {
        "template_id": "date_consistency_9file",
        "name": "9文件日期一致性",
        "category": "一致性校验",
        "level": "高",
        "clause": "申请日期≤招待日期≤开票日期/支付时间/报销日期，函件日期相近",
        "description": "校验 9 个文件之间的日期时序关系",
        "check_expression": json.dumps({
            "type": "cross_field_compare",
            "field": "招待日期",
            "field_slot": "审批单",
            "field_type": "date",
            "comparisons": [
                {"other_slot": "申请单", "other_field": "申请日期", "operator": "<=", "message": "申请日期应早于或等于招待日期"},
                {"other_slot": "发票XML", "other_field": "开票日期", "fallback_slot": "发票PDF", "operator": "<=", "message": "发票日期应不晚于招待日期"},
                {"other_slot": "支付凭证", "other_field": "支付时间", "operator": ">=", "message": "支付时间应不早于招待日期"},
                {"other_slot": "支付流水", "other_field": "交易时间", "operator": ">=", "message": "流水时间应不早于招待日期"},
                {"other_slot": "报账单", "other_field": "报销日期", "operator": ">=", "message": "报销日期应不早于招待日期"},
                {"other_slot": "活动函件", "other_field": "交流时间", "operator": "~", "tolerance_days": 7, "message": "活动函件日期应与招待日期相近(±7天)"},
            ]
        }, ensure_ascii=False),
    },
    {
        "template_id": "amount_consistency",
        "name": "金额一致性（发票 vs 各单据）",
        "category": "一致性校验",
        "level": "高",
        "clause": "以发票小写金额为准，审批单、支付凭证、支付流水、报账单金额应一致",
        "description": "核对发票金额与各单据金额是否一致（容差0.01元）",
        "check_expression": json.dumps({
            "type": "cross_field_compare",
            "field": "价税合计小写",
            "field_slot": "发票XML",
            "fallback_slot": "发票PDF",
            "field_type": "number",
            "tolerance": 0.01,
            "comparisons": [
                {"other_slot": "审批单", "other_field": "招待金额", "operator": "==", "message": "审批单金额应与发票一致"},
                {"other_slot": "支付凭证", "other_field": "金额", "operator": "==", "message": "支付凭证金额应与发票一致"},
                {"other_slot": "支付流水", "other_field": "金额", "operator": "==", "message": "支付流水金额应与发票一致"},
                {"other_slot": "报账单", "other_field": "合计金额", "operator": "==", "message": "报账单金额应与发票一致"},
            ]
        }, ensure_ascii=False),
    },
    {
        "template_id": "companion_limit_external",
        "name": "陪同人数上限（外部招待）",
        "category": "合规性校验",
        "level": "高",
        "clause": "外部招待陪同人数：对象≤5人对等，>5人时 guest+(guest-5)//2",
        "description": "校验外部招待陪同人数是否符合标准",
        "check_expression": json.dumps({
            "type": "cross_field_compare",
            "field": "招待人数",
            "field_slot": "审批单",
            "field_type": "number",
            "comparisons": [
                {"other_slot": "审批单", "other_field": "陪同人数", "operator": ">=", "message": "陪同人数不应超过招待人数太多"}
            ]
        }, ensure_ascii=False),
    },
    {
        "template_id": "forbidden_places",
        "name": "禁止场所关键词检测",
        "category": "禁止性规定",
        "level": "高",
        "clause": "商户名称不应包含禁止场所关键词",
        "description": "检测商户名称是否命中私人会所、高档娱乐等禁止场所",
        "check_expression": json.dumps({
            "type": "keyword_match",
            "field": "商户全称",
            "field_slot": "支付凭证",
            "keywords": ["私人会所", "一桌餐", "一围餐", "高档娱乐", "高档小区", "写字楼", "烟酒专卖店", "农家乐", "宿舍", "保健", "健身"],
            "mode": "any",
        }, ensure_ascii=False),
    },
    {
        "template_id": "forbidden_foods",
        "name": "禁止食材关键词检测",
        "category": "禁止性规定",
        "level": "高",
        "clause": "消费明细不应包含禁止食材",
        "description": "检测原始文本是否命中鱼翅、燕窝等禁止食材关键词",
        "check_expression": json.dumps({
            "type": "keyword_match",
            "field": "",  # 空字段名表示搜索所有槽位
            "field_slot": "",
            "keywords": ["鱼翅", "燕窝", "野生保护动物", "珍稀药材"],
            "mode": "any",
        }, ensure_ascii=False),
    },
    {
        "template_id": "alcohol_tobacco",
        "name": "烟酒消费检测",
        "category": "禁止性规定",
        "level": "中",
        "clause": "不应包含烟酒消费",
        "description": "检测商户名称或原始文本是否包含烟酒相关关键词",
        "check_expression": json.dumps({
            "type": "keyword_match",
            "field": "商户全称",
            "field_slot": "支付凭证",
            "keywords": ["烟", "酒", "白酒", "红酒", "葡萄酒", "高档酒水"],
            "mode": "any",
        }, ensure_ascii=False),
    },
    {
        "template_id": "gift_detection",
        "name": "礼品礼金检测",
        "category": "禁止性规定",
        "level": "高",
        "clause": "不应包含礼品礼金类消费",
        "description": "检测是否包含现金、购物卡、会员卡等礼品礼金关键词",
        "check_expression": json.dumps({
            "type": "keyword_match",
            "field": "商户全称",
            "field_slot": "支付凭证",
            "keywords": ["现金", "购物卡", "会员卡", "预付卡", "有价证券", "名贵土特产", "珠宝", "玉石"],
            "mode": "any",
        }, ensure_ascii=False),
    },
    {
        "template_id": "business_status_builtin",
        "name": "单位经营状态（内置）",
        "category": "经营风险",
        "level": "提示",
        "clause": "招待单位应处于正常经营状态",
        "description": "检查招待单位是否正常经营（使用内置规则函数）",
        "check_expression": "business_status",  # 硬编码函数名
    },
]


@router.get("/admin/review-rules/templates")
def get_rule_templates(_admin: User = Depends(get_admin_user)):
    """获取系统预置规则模板列表"""
    return [
        {
            "template_id": t["template_id"],
            "name": t["name"],
            "category": t["category"],
            "level": t["level"],
            "clause": t["clause"],
            "description": t["description"],
            "is_builtin": t["check_expression"] not in ["cross_field_compare", "keyword_match", "amount_threshold"]
                             and "{" not in t["check_expression"],
        }
        for t in RULE_TEMPLATES
    ]


@router.post("/admin/review-rules/apply-template")
def apply_rule_template(
    data: dict,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """应用规则模板 — 创建一条规则（如已存在则跳过）
    Body: {"template_id": "..."} 或 {"template_ids": ["...", "..."]}
    """
    template_ids = data.get("template_ids") or [data.get("template_id", "")]
    applied = []
    skipped = []

    for tid in template_ids:
        tmpl = next((t for t in RULE_TEMPLATES if t["template_id"] == tid), None)
        if not tmpl:
            skipped.append({"template_id": tid, "reason": "模板不存在"})
            continue

        # 检查是否已存在（按 rule_name 去重）
        existing = db.query(AuditRule).filter(AuditRule.rule_name == tmpl["name"]).first()
        if existing:
            skipped.append({"template_id": tid, "reason": f"规则'{tmpl['name']}'已存在"})
            continue

        rule = AuditRule(
            category=tmpl["category"],
            rule_name=tmpl["name"],
            clause=tmpl["clause"],
            level=tmpl["level"],
            description=tmpl["description"],
            check_expression=tmpl["check_expression"],
            source_document="模板应用",
            enabled=True,
            created_by=_admin.id,
        )
        db.add(rule)
        applied.append(tid)

    db.commit()

    return {
        "applied": applied,
        "skipped": skipped,
        "detail": f"成功应用 {len(applied)} 条规则，跳过 {len(skipped)} 条",
    }


# ===================================================================
# Excel 批量导入
# ===================================================================

@router.post("/admin/review-rules/import-excel")
def import_rules_from_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """从 Excel 文件批量导入审核规则

    Excel 列格式:
    分类 | 规则名称 | 级别 | 规则条款 | 详细说明 | 规则类型 | 基准槽位 | 基准字段 | 比较槽位 | 比较字段 | 运算符 | 容差 | fallback槽位 | 关键词 | 匹配模式
    """
    if not file.filename:
        raise HTTPException(400, "未选择文件")

    ext = Path(file.filename).suffix.lower()
    if ext not in (".xlsx", ".xls"):
        raise HTTPException(400, f"不支持的文件类型: {ext}，请上传 Excel 文件")

    content_bytes = file.file.read()
    file.file.close()

    try:
        from openpyxl import load_workbook
    except ImportError:
        raise HTTPException(500, "openpyxl 未安装，无法导入 Excel")

    try:
        wb = load_workbook(filename=Path(__file__).parent / "_tmp_import.xlsx")
        wb.close()
    except Exception:
        pass

    # 保存临时文件
    tmp_path = Path(__file__).parent / "_tmp_import.xlsx"
    tmp_path.write_bytes(content_bytes)

    try:
        wb = load_workbook(filename=str(tmp_path), read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(min_row=1, values_only=True))
        wb.close()
        tmp_path.unlink(missing_ok=True)

        if len(rows) < 2:
            raise HTTPException(400, "Excel 文件为空或没有数据行")

        # 解析表头
        headers = [str(h).strip() if h else "" for h in rows[0]]
        required = ["分类", "规则名称", "级别", "规则类型"]
        for req in required:
            if req not in headers:
                raise HTTPException(400, f"缺少必需列: {req}，当前列: {headers}")

        hidx = {h: i for i, h in enumerate(headers)}

        # 按规则名称分组（同一规则名称的多行合并为一条规则的比较条件）
        from collections import defaultdict
        rule_groups = defaultdict(list)

        for row_idx, row in enumerate(rows[1:], start=2):
            if not any(row):
                continue

            def get_col(name, default=""):
                idx = hidx.get(name)
                if idx is not None and idx < len(row) and row[idx]:
                    return str(row[idx]).strip()
                return default

            category = get_col("分类", "自定义")
            rule_name = get_col("规则名称")
            level = get_col("级别", "高")
            clause = get_col("规则条款", "")
            description = get_col("详细说明", "")
            rule_type = get_col("规则类型")

            if not rule_name:
                continue

            rule_groups[rule_name].append({
                "row": row_idx,
                "category": category,
                "rule_name": rule_name,
                "level": level,
                "clause": clause,
                "description": description,
                "rule_type": rule_type,
                "base_slot": get_col("基准槽位"),
                "base_field": get_col("基准字段"),
                "other_slot": get_col("比较槽位"),
                "other_field": get_col("比较字段"),
                "operator": get_col("运算符", "=="),
                "tolerance": get_col("容差", "0"),
                "fallback_slot": get_col("fallback槽位"),
                "keywords": get_col("关键词"),
                "mode": get_col("匹配模式", "any"),
                "message": get_col("消息", get_col("规则条款")),
            })

        # 转换为规则并写入数据库
        created = []
        errors = []

        for rule_name, entries in rule_groups.items():
            first = entries[0]
            rule_type = first["rule_type"]

            try:
                if rule_type in ("cross_compare", "cross_field_compare"):
                    check_expr = _build_cross_compare_expr(entries)
                elif rule_type in ("keyword", "keyword_match"):
                    check_expr = _build_keyword_match_expr(entries)
                elif rule_type in ("threshold", "amount_threshold"):
                    check_expr = _build_amount_threshold_expr(entries)
                elif rule_type in ("", "builtin", "系统内置", None):
                    # 硬编码函数名
                    check_expr = first.get("基准字段", "") or first.get("运算符", "")
                else:
                    errors.append(f"第{first['row']}行: 未知规则类型 '{rule_type}'")
                    continue

                # 检查是否已存在
                existing = db.query(AuditRule).filter(AuditRule.rule_name == rule_name).first()
                if existing:
                    # 更新
                    existing.check_expression = check_expr
                    existing.category = first["category"]
                    existing.clause = first["clause"]
                    existing.level = first["level"]
                    existing.description = first["description"]
                    existing.updated_at = datetime.now().isoformat()
                    created.append({"rule_name": rule_name, "action": "updated"})
                else:
                    rule = AuditRule(
                        category=first["category"],
                        rule_name=rule_name,
                        clause=first["clause"],
                        level=first["level"],
                        description=first["description"],
                        check_expression=check_expr,
                        source_document="Excel导入",
                        enabled=True,
                        created_by=_admin.id,
                    )
                    db.add(rule)
                    created.append({"rule_name": rule_name, "action": "created"})

            except Exception as e:
                errors.append(f"规则'{rule_name}'导入失败: {str(e)}")

        db.commit()

        return {
            "detail": f"导入完成：{len(created)} 条规则成功，{len(errors)} 条失败",
            "created": created,
            "errors": errors,
        }

    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(400, f"Excel 解析失败: {str(e)}")


def _build_cross_compare_expr(entries):
    """从 Excel 条目构建 cross_field_compare JSON 表达式"""
    first = entries[0]
    base_slot = first["base_slot"]
    base_field = first["base_field"]

    # 判断字段类型
    field_type = "date"
    if first["base_field"] and any(k in first["base_field"] for k in ["金额", "费用", "人均", "税额"]):
        field_type = "number"

    comparisons = []
    for e in entries:
        if e["other_slot"] and e["other_field"]:
            comp = {
                "other_slot": e["other_slot"],
                "other_field": e["other_field"],
                "operator": e["operator"],
            }
            if e["message"]:
                comp["message"] = e["message"]
            if e["fallback_slot"]:
                comp["fallback_slot"] = e["fallback_slot"]
            if e["tolerance"]:
                try:
                    comp["tolerance_days" if field_type == "date" else "tolerance"] = float(e["tolerance"])
                except ValueError:
                    pass
            comparisons.append(comp)

    return json.dumps({
        "type": "cross_field_compare",
        "field": base_field,
        "field_slot": base_slot,
        "field_type": field_type,
        "comparisons": comparisons,
    }, ensure_ascii=False)


def _build_keyword_match_expr(entries):
    """从 Excel 条目构建 keyword_match JSON 表达式"""
    first = entries[0]
    all_keywords = []
    for e in entries:
        if e["keywords"]:
            all_keywords.extend([k.strip() for k in e["keywords"].split(",") if k.strip()])

    return json.dumps({
        "type": "keyword_match",
        "field": first.get("base_field", ""),
        "field_slot": first.get("base_slot", ""),
        "keywords": all_keywords,
        "mode": first.get("mode", "any"),
    }, ensure_ascii=False)


def _build_amount_threshold_expr(entries):
    """从 Excel 条目构建 amount_threshold JSON 表达式"""
    first = entries[0]
    threshold = 0
    if first.get("tolerance"):
        try:
            threshold = float(first["tolerance"])
        except ValueError:
            pass

    return json.dumps({
        "type": "amount_threshold",
        "field": first.get("base_field", ""),
        "field_slot": first.get("base_slot", ""),
        "operator": first.get("operator", ">"),
        "threshold": threshold,
    }, ensure_ascii=False)


# ===================================================================
# Excel 模板下载
# ===================================================================

@router.get("/admin/review-rules/import-template")
def download_import_template(_admin: User = Depends(get_admin_user)):
    """下载 Excel 导入模板文件"""
    try:
        from openpyxl import Workbook
    except ImportError:
        raise HTTPException(500, "openpyxl 未安装")

    wb = Workbook()
    ws = wb.active
    ws.title = "审核规则导入模板"

    # 表头
    headers = ["分类", "规则名称", "级别", "规则条款", "详细说明", "规则类型",
               "基准槽位", "基准字段", "比较槽位", "比较字段", "运算符", "容差",
               "fallback槽位", "关键词", "匹配模式", "消息"]
    ws.append(headers)

    # 示例行 1: 跨字段比较（日期）
    ws.append(["一致性校验", "9文件日期一致性", "高", "日期时序关系校验",
               "校验各文件之间的日期时序", "cross_compare",
               "审批单", "招待日期", "申请单", "申请日期", "<=", "", "", "", ""])
    ws.append(["一致性校验", "9文件日期一致性", "高", "日期时序关系校验",
               "", "cross_compare",
               "审批单", "招待日期", "发票XML", "开票日期", "<=", "", "发票PDF", "", ""])
    ws.append(["一致性校验", "9文件日期一致性", "高", "日期时序关系校验",
               "", "cross_compare",
               "审批单", "招待日期", "支付凭证", "支付时间", ">=", "", "", "", ""])

    # 示例行 2: 金额比较
    ws.append(["一致性校验", "金额一致性", "高", "各单据金额应与发票一致",
               "容差0.01元", "cross_compare",
               "发票XML", "价税合计小写", "审批单", "招待金额", "==", "0.01", "发票PDF", "", ""])

    # 示例行 3: 关键词匹配
    ws.append(["禁止性规定", "禁止场所检测", "高", "商户名不应含禁止场所",
               "", "keyword_match",
               "支付凭证", "商户全称", "", "", "", "", "", "私人会所,高档娱乐,烟酒专卖店", "any", ""])

    # 示例行 4: 金额阈值
    ws.append(["合规性校验", "人均费用上限", "高", "人均费用不应超过标准",
               "", "amount_threshold",
               "审批单", "人均费用", "", "", ">", "400", "", "", "", "人均费用超过400元标准"])

    # 设置表头样式
    from openpyxl.styles import Font
    for cell in ws[1]:
        cell.font = Font(bold=True)

    import io
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="审核规则导入模板.xlsx"',
        },
    )

