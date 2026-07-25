"""申请单生成模块 — 根据场景模板生成业务招待申请单"""

from .form_fields import FORM_CATEGORIES
from .generator import FormGenerator

__all__ = ["FORM_CATEGORIES", "FormGenerator"]
