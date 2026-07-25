"""接待标准查询函数 — 经办人填写申请单前快速查询"""

from . import standards


def lookup_external_standards(personnel_level: str, reception_type: str) -> dict | None:
    """查询对外业务招待标准

    Args:
        personnel_level: 人员层级 — "省管中层" / "市管中层" / "其他人员"
        reception_type: 招待类型 — "商务招待" / "外事招待" / "其他公务招待"

    Returns:
        标准字典，未匹配返回 None
    """
    category = "外事/商务" if reception_type in ("商务招待", "外事招待") else "其他公务"
    for std in standards.EXTERNAL_STANDARDS:
        if std.personnel_level == personnel_level and std.reception_type == category:
            return std.to_dict()
    return None


def lookup_internal_standards(personnel_level: str) -> dict | None:
    """查询内部业务招待标准

    Args:
        personnel_level: 人员层级

    Returns:
        标准字典，未匹配返回 None
    """
    for std in standards.INTERNAL_STANDARDS:
        if std.personnel_level == personnel_level:
            return std.to_dict()
    return None


def lookup_companion_rule(reception_type: str) -> dict | None:
    """查询陪同人数规则

    Args:
        reception_type: "外部" 或 "内部"

    Returns:
        规则字典
    """
    if reception_type == "外部":
        rule = standards.COMPANION_RULES[0]
        return {
            "规则": rule.rule_desc,
            "计算公式": rule.companion_formula,
            "依据": "第十二条",
        }
    elif reception_type == "内部":
        rule = standards.COMPANION_RULES[1]
        return {
            "规则": rule.rule_desc,
            "计算公式": rule.companion_formula,
            "依据": "第十三条",
        }
    return None


def calculate_companion_limit(guest_count: int, reception_type: str) -> dict:
    """根据招待对象人数计算陪同人数上限

    Args:
        guest_count: 招待对象人数
        reception_type: "外部" 或 "内部"

    Returns:
        计算结果字典
    """
    if reception_type == "外部":
        if guest_count <= 5:
            limit = guest_count
            desc = "对等"
        else:
            limit = 5 + (guest_count - 5) // 2
            desc = f"超出部分1/2"
        return {
            "招待对象人数": guest_count,
            "陪同人数上限": limit,
            "规则": desc,
            "类型": "外部招待",
            "依据": "第十二条",
        }
    else:
        if guest_count <= 10:
            limit = 3
            desc = "上限3人"
        else:
            limit = guest_count // 3
            desc = f"对象的1/3"
        return {
            "招待对象人数": guest_count,
            "陪同人数上限": limit,
            "规则": desc,
            "类型": "内部招待",
            "依据": "第十三条",
        }


def get_reception_type_explanations() -> list[dict]:
    """获取所有招待类型说明"""
    return standards.RECEPTION_TYPE_EXPLANATIONS


def get_prohibitions() -> list[dict]:
    """获取禁止性规定汇总"""
    return standards.PROHIBITIONS


def get_approval_flow() -> list[dict]:
    """获取审批流程"""
    return standards.APPROVAL_FLOW


def get_holiday_reporting() -> dict:
    """获取节假日报备信息"""
    return standards.HOLIDAY_REPORTING


def quick_lookup(
    personnel_level: str,
    reception_type: str,
    guest_count: int | None = None,
) -> dict:
    """一键查询 — 根据人员层级和招待类型返回完整标准

    经办人只需填写：
    - 陪同人员最高级别（省管中层 / 市管中层 / 其他人员）
    - 招待类型（商务招待 / 外事招待 / 其他公务招待 / 内部业务招待）

    Returns:
        包含所有相关标准的字典
    """
    result: dict = {
        "人员层级": personnel_level,
        "招待类型": reception_type,
    }

    # 查找对应类型说明
    for info in standards.RECEPTION_TYPE_EXPLANATIONS:
        if info["类型"] == reception_type:
            result["类型说明"] = info["说明"]
            result["适用标准"] = info["适用标准"]
            result["注意事项"] = info["注意事项"]
            break

    # 查找金额标准
    if reception_type in ("商务招待", "外事招待", "其他公务招待"):
        std = lookup_external_standards(personnel_level, reception_type)
        if std:
            result.update(std)
    elif reception_type == "内部业务招待":
        std = lookup_internal_standards(personnel_level)
        if std:
            result.update(std)

    # 陪同人数规则
    if guest_count is not None:
        comp = calculate_companion_limit(guest_count, "外部" if reception_type != "内部业务招待" else "内部")
        result["陪同人数计算"] = comp

    return result
