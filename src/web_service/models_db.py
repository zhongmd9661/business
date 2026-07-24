"""SQLAlchemy 数据模型"""
import json
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")  # 'user' or 'admin'
    created_at = Column(String, default=lambda: datetime.now().isoformat())


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    batch_name = Column(String, nullable=False)
    status = Column(String, default="pending")
    file_count = Column(Integer, default=0)
    output_dir = Column(String)
    error_message = Column(Text)
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    completed_at = Column(String)


class TaskFile(Base):
    __tablename__ = "task_files"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String)
    parsed = Column(Boolean, default=False)
    md_path = Column(String)


class AuditRule(Base):
    __tablename__ = "audit_rules"

    id = Column(Integer, primary_key=True)
    category = Column(String, nullable=False)
    rule_name = Column(String, nullable=False)
    clause = Column(String, nullable=False)
    level = Column(String, nullable=False)
    description = Column(Text)
    check_expression = Column(Text)
    source_document = Column(String)
    enabled = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat())


class AuditRuleHistory(Base):
    __tablename__ = "audit_rule_history"

    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey("audit_rules.id"), nullable=False)
    action = Column(String, nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    changed_by = Column(Integer, ForeignKey("users.id"))
    changed_at = Column(String, default=lambda: datetime.now().isoformat())


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True)
    document_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    last_mtime = Column(Float, default=0.0)
    version_tag = Column(String)
    parsed_at = Column(String, default=lambda: datetime.now().isoformat())
    sync_status = Column(String, default="synced")
    sync_diff = Column(Text)
    applied_by = Column(Integer, ForeignKey("users.id"))
    applied_at = Column(String)


class SyncHistory(Base):
    __tablename__ = "sync_history"

    id = Column(Integer, primary_key=True)
    trigger_type = Column(String, nullable=False)
    document_name = Column(String, nullable=False)
    rules_added = Column(Integer, default=0)
    rules_modified = Column(Integer, default=0)
    rules_deleted = Column(Integer, default=0)
    diff_report = Column(Text)
    status = Column(String, default="pending")
    operated_by = Column(Integer, ForeignKey("users.id"))
    operated_at = Column(String, default=lambda: datetime.now().isoformat())


class ReceptionStandard(Base):
    """接待标准存储表 — 管理员可修改"""

    __tablename__ = "reception_standards"

    id = Column(Integer, primary_key=True)
    category = Column(String, nullable=False)  # "external" or "internal"
    sub_category = Column(String, nullable=False)  # "外事/商务" or "其他公务"
    personnel_level = Column(String, nullable=False)  # "省管中层" / "市管中层" / "其他人员"
    meal_limit = Column(Float, default=0.0)  # 用餐人均上限
    souvenir_limit = Column(Float, nullable=True)  # 纪念品上限，NULL表示不得赠送
    baijiu_limit = Column(Float, default=0.0)  # 白酒上限
    red_wine_limit = Column(Float, default=0.0)  # 红酒上限
    enabled = Column(Boolean, default=True)
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_by = Column(Integer, ForeignKey("users.id"))


class ReceptionStandardHistory(Base):
    """接待标准修改历史"""

    __tablename__ = "reception_standard_history"

    id = Column(Integer, primary_key=True)
    standard_id = Column(Integer, ForeignKey("reception_standards.id"), nullable=False)
    action = Column(String, nullable=False)  # "create" / "update" / "delete"
    old_values = Column(Text)  # JSON
    new_values = Column(Text)  # JSON
    changed_by = Column(Integer, ForeignKey("users.id"))
    changed_at = Column(String, default=lambda: datetime.now().isoformat())


class ReceptionTemplate(Base):
    """场景接待模板存储表"""

    __tablename__ = "reception_templates"

    id = Column(Integer, primary_key=True)
    template_id = Column(String, unique=True, nullable=False)  # unique key
    title = Column(String, nullable=False)
    icon = Column(String)
    icon_class = Column(String)
    reception_type = Column(String, nullable=False)
    category = Column(String)
    example_data = Column(Text)  # JSON
    notes = Column(Text)
    required_docs = Column(Text)
    enabled = Column(Boolean, default=True)
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_by = Column(Integer, ForeignKey("users.id"))


class ReceptionRecord(Base):
    """招待费提交记录 — 由 card7-fill.html 表单提交"""

    __tablename__ = "reception_records"

    id = Column(Integer, primary_key=True)
    serial_number = Column(String, unique=True, nullable=False)  # 提交流水号，如 ZDF-20260724-0001
    scenario = Column(String, nullable=False)  # A/B/C/D/E/F
    scenario_name = Column(String, nullable=False)
    submitter = Column(String, default="匿名")
    date = Column(String)  # 招待日期
    location = Column(String)
    org = Column(String)  # 招待对象单位
    guests = Column(Integer)  # 招待对象人数
    accompany_people = Column(String)  # 陪同人员
    accompany_count = Column(Integer)  # 陪同人数
    per_capita = Column(Float)  # 人均消费
    total_amount = Column(Float)  # 总金额
    baijiu_price = Column(String)  # 白酒单价
    wine_price = Column(String)  # 葡萄酒单价
    gift_per = Column(String)  # 礼品单价
    rooms = Column(String)  # 房间数
    room_price = Column(String)  # 房价
    reason = Column(Text)  # 事由
    nationality = Column(String)  # 外事招待-国籍
    fee = Column(String)  # 工作餐-费用
    status = Column(String, default="pending")  # pending / approved / rejected
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat())


# --- Engine & Session ---

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    _seed_default_rules()
    _ensure_standards_seeded()
    _ensure_templates_seeded()


def _ensure_standards_seeded():
    """确保标准数据已注入（独立于规则注入）"""
    db = SessionLocal()
    try:
        if db.query(ReceptionStandard).first():
            return
        _seed_default_standards(db)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _ensure_templates_seeded():
    """确保模板数据已注入（独立于规则注入）"""
    db = SessionLocal()
    try:
        if db.query(ReceptionTemplate).first():
            return
        _seed_default_templates(db)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _seed_default_rules():
    """首次启动时从制度文档解析规则到数据库"""
    # Lazy import to avoid circular deps
    from .config import RULES_DIR
    from .rule_parser import parse_all_documents

    import json
    import os

    db = SessionLocal()
    try:
        if db.query(AuditRule).first():
            return

        rules = parse_all_documents()
        for rule_data in rules:
            rule = AuditRule(
                category=rule_data.get("category", ""),
                rule_name=rule_data.get("rule_name", ""),
                clause=rule_data.get("clause", ""),
                level=rule_data.get("level", "中"),
                description=rule_data.get("description", ""),
                check_expression=rule_data.get("check_expression", ""),
                source_document=rule_data.get("source_document", ""),
                enabled=True,
            )
            db.add(rule)

        for fpath in RULES_DIR.glob("*.docx"):
            dv = DocumentVersion(
                document_name=fpath.stem,
                file_path=str(fpath),
                last_mtime=os.path.getmtime(fpath),
                sync_status="synced",
            )
            db.add(dv)

        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _seed_default_standards(db: Session):
    """从 defaults 注入默认接待标准"""
    defaults = [
        # 对外
        {"category": "external", "sub_category": "外事/商务", "personnel_level": "省管中层", "meal_limit": 400.0, "souvenir_limit": 400.0, "baijiu_limit": 400.0, "red_wine_limit": 400.0},
        {"category": "external", "sub_category": "其他公务", "personnel_level": "省管中层", "meal_limit": 200.0, "souvenir_limit": None, "baijiu_limit": 400.0, "red_wine_limit": 400.0},
        {"category": "external", "sub_category": "外事/商务", "personnel_level": "市管中层", "meal_limit": 300.0, "souvenir_limit": 300.0, "baijiu_limit": 300.0, "red_wine_limit": 300.0},
        {"category": "external", "sub_category": "其他公务", "personnel_level": "市管中层", "meal_limit": 200.0, "souvenir_limit": None, "baijiu_limit": 300.0, "red_wine_limit": 300.0},
        {"category": "external", "sub_category": "外事/商务", "personnel_level": "其他人员", "meal_limit": 200.0, "souvenir_limit": 200.0, "baijiu_limit": 200.0, "red_wine_limit": 200.0},
        {"category": "external", "sub_category": "其他公务", "personnel_level": "其他人员", "meal_limit": 150.0, "souvenir_limit": None, "baijiu_limit": 200.0, "red_wine_limit": 200.0},
        # 内部
        {"category": "internal", "sub_category": "", "personnel_level": "省管中层", "meal_limit": 150.0, "souvenir_limit": None, "baijiu_limit": 0.0, "red_wine_limit": 0.0},
        {"category": "internal", "sub_category": "", "personnel_level": "市管中层", "meal_limit": 150.0, "souvenir_limit": None, "baijiu_limit": 0.0, "red_wine_limit": 0.0},
        {"category": "internal", "sub_category": "", "personnel_level": "其他人员", "meal_limit": 100.0, "souvenir_limit": None, "baijiu_limit": 0.0, "red_wine_limit": 0.0},
    ]
    for d in defaults:
        db.add(ReceptionStandard(**d))


def _seed_default_templates(db: Session):
    """从 defaults 注入默认场景模板"""
    from ..standards_query import templates

    for t in templates.get_templates():
        db.add(ReceptionTemplate(
            template_id=t["id"],
            title=t["title"],
            icon=t["icon"],
            icon_class=t["icon_class"],
            reception_type=t["reception_type"],
            category=t["category"],
            example_data=json.dumps(t["example"], ensure_ascii=False),
            notes=t["notes"],
            required_docs=t["required_docs"],
        ))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
