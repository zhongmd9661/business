"""申请单字段定义 — 所有场景共享的表单字段结构"""

# 申请单字段分组定义
FORM_CATEGORIES = [
    {
        "id": "basic",
        "title": "基本信息",
        "icon": "📋",
        "fields": [
            {"key": "application_no", "label": "申请单号", "type": "text", "required": True, "placeholder": "系统自动生成"},
            {"key": "applicant", "label": "申请人", "type": "text", "required": True, "placeholder": "请输入姓名"},
            {"key": "department", "label": "申请部门", "type": "text", "required": True, "placeholder": "请输入部门名称"},
            {"key": "position", "label": "职务/职级", "type": "select", "required": True,
             "options": ["省管中层", "市管中层", "其他人员"]},
            {"key": "application_date", "label": "申请日期", "type": "date", "required": True},
        ],
    },
    {
        "id": "reception",
        "title": "招待信息",
        "icon": "🍽️",
        "fields": [
            {"key": "reception_type", "label": "招待类型", "type": "select", "required": True,
             "options": ["商务招待", "外事招待", "其他公务招待", "内部业务招待", "工作餐"]},
            {"key": "reception_category", "label": "招待类别", "type": "select", "required": True,
             "options": ["对外业务招待", "内部业务招待"]},
            {"key": "reason", "label": "招待事由", "type": "textarea", "required": True, "placeholder": "请详细说明招待事由"},
            {"key": "guest_info", "label": "招待对象", "type": "text", "required": True, "placeholder": "单位名称 + 姓名 + 人数，如：XX公司 张总等5人"},
            {"key": "guest_count", "label": "招待人数", "type": "number", "required": True, "placeholder": "纯数字"},
            {"key": "date", "label": "招待日期", "type": "date", "required": True},
            {"key": "time_period", "label": "用餐时段", "type": "select", "required": True,
             "options": ["早餐", "午餐", "晚餐"]},
            {"key": "venue", "label": "用餐地点", "type": "text", "required": True, "placeholder": "餐厅名称或地址"},
            {"key": "is_holiday", "label": "是否节假日", "type": "boolean", "required": True},
        ],
    },
    {
        "id": "companion",
        "title": "陪同人员",
        "icon": "👥",
        "fields": [
            {"key": "companion_list", "label": "陪同人员", "type": "textarea", "required": True,
             "placeholder": "姓名 + 职务，每行一人，如：\n李经理（市管中层）\n王主管\n赵专员"},
            {"key": "companion_count", "label": "陪同人数", "type": "number", "required": True, "placeholder": "纯数字"},
            {"key": "companion_limit_info", "label": "陪同人数规定", "type": "readonly", "required": False},
        ],
    },
    {
        "id": "budget",
        "title": "费用预算",
        "icon": "💰",
        "fields": [
            {"key": "per_person_limit", "label": "人均标准", "type": "readonly", "required": False},
            {"key": "per_person_actual", "label": "人均金额（元）", "type": "number", "required": True, "placeholder": "预计人均金额"},
            {"key": "total_amount", "label": "预计总金额（元）", "type": "readonly", "required": False},
            {"key": "accommodation", "label": "住宿安排", "type": "textarea", "required": False, "placeholder": "房间类型 + 数量 + 标准"},
            {"key": "transport", "label": "用车安排", "type": "textarea", "required": False, "placeholder": "车辆来源 + 用途"},
            {"key": "alcohol", "label": "酒水情况", "type": "select", "required": True,
             "options": ["无酒水", "白酒", "红酒", "白酒+红酒"]},
            {"key": "alcohol_detail", "label": "酒水明细", "type": "textarea", "required": False,
             "placeholder": "如：白酒 500ml × 2瓶，红酒 750ml × 1瓶"},
            {"key": "souvenir", "label": "纪念品", "type": "select", "required": True,
             "options": ["无纪念品", "有纪念品"]},
            {"key": "souvenir_detail", "label": "纪念品明细", "type": "textarea", "required": False,
             "placeholder": "物品名称 + 数量 + 单价"},
        ],
    },
    {
        "id": "approval",
        "title": "审批信息",
        "icon": "✅",
        "fields": [
            {"key": "pre_approval", "label": "事前审批", "type": "select", "required": True,
             "options": ["已审批", "待审批", "紧急后补"]},
            {"key": "approver", "label": "审批人", "type": "text", "required": False, "placeholder": "审批领导姓名"},
            {"key": "approval_opinion", "label": "审批意见", "type": "textarea", "required": False, "placeholder": "领导审批意见"},
            {"key": "attachment_notes", "label": "附件说明", "type": "textarea", "required": False,
             "placeholder": "如：事前审批单、活动公函、费用明细清单等"},
        ],
    },
]

# 字段映射：模板字段名 → 申请单字段名
TEMPLATE_TO_FORM = {
    "招待类型": "reception_type",
    "招待事由": "reason",
    "招待对象": "guest_info",
    "招待人数": "guest_count",
    "陪同人数上限": "companion_count",
    "陪同人员": "companion_list",
    "人均标准": "per_person_limit",
    "预计总费用": "total_amount",
    "用餐地点": "venue",
    "酒水标准": "alcohol",
    "纪念品标准": "souvenir",
    "酒水": "alcohol",
    "酒水明细": "alcohol_detail",
    "用餐标准": "per_person_limit",
    "住宿安排": "accommodation",
    "用车安排": "transport",
}

# 只读字段（自动计算/展示）
READONLY_FIELDS = {"per_person_limit", "total_amount", "companion_limit_info"}

# 申请单号生成规则
APPLICATION_NO_PREFIX = "JD"  # 招待
APPLICATION_NO_TEMPLATE = "JD{year}{month}{day}{seq:04d}"
