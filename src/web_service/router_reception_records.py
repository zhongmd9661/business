"""招待费提交记录 API"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from jose import JWTError, jwt
from pydantic import BaseModel

from .auth import get_admin_user, get_current_user
from .config import JWT_ALGORITHM, JWT_SECRET_KEY
from .models_db import ReceptionRecord, SessionLocal, User

router = APIRouter()


class CurrentUserOrAnonymous:
    """Optional auth — returns User if valid token, otherwise None"""
    def __init__(
        self,
        token: Optional[str] = Query(None, alias="token"),
    ):
        self.user: Optional[User] = None
        if token:
            try:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                user_id = int(payload["sub"])
                db = SessionLocal()
                try:
                    self.user = db.query(User).filter(User.id == user_id).first()
                finally:
                    db.close()
            except (JWTError, ValueError):
                pass


def get_optional_user(request: Request) -> Optional[User]:
    """Read token from Authorization header; return User or None."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    else:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
        db = SessionLocal()
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()
    except (JWTError, ValueError):
        return None


def _camel_to_snake(d):
    """前端字段名 camelCase → 后端 snake_case 兼容转换"""
    mapping = {
        "accompanyPeople": "accompany_people",
        "accompanyCount": "accompany_count",
        "perCapita": "per_capita",
        "baijiuPrice": "baijiu_price",
        "winePrice": "wine_price",
        "giftPer": "gift_per",
        "roomPrice": "room_price",
        "scenarioName": "scenario_name",
        "totalAmount": "total_amount",
        "createdAt": "created_at",
        "updatedAt": "updated_at",
    }
    result = {}
    for k, v in d.items():
        result[mapping.get(k, k)] = v
    return result


@router.post("/reception-records")
async def create_record(request: Request):
    """提交一条招待费记录，自动生成流水号"""
    body_bytes = await request.body()
    try:
        payload = __import__("json").loads(body_bytes.decode("utf-8"))
    except UnicodeDecodeError:
        payload = __import__("json").loads(body_bytes.decode("gbk"))
    payload = _camel_to_snake(payload)

    # Auto-fill submitter from JWT token if not provided
    current_user = get_optional_user(request)
    if not payload.get("submitter") and current_user:
        payload["submitter"] = current_user.username

    session = SessionLocal()
    try:
        # 生成流水号: ZDF-YYYYMMDD-NNNN
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"ZDF-{today}-"
        last = (
            session.query(ReceptionRecord)
            .filter(ReceptionRecord.serial_number.like(f"{prefix}%"))
            .order_by(ReceptionRecord.serial_number.desc())
            .first()
        )
        if last:
            seq = int(last.serial_number.split("-")[-1]) + 1
        else:
            seq = 1
        serial_number = f"{prefix}{seq:04d}"

        # 计算总金额（如果前端没传）
        per_capita = float(payload.get("per_capita") or 0)
        guests = int(payload.get("guests") or 0)
        accompany_count = int(payload.get("accompany_count") or 0)
        total_amount = payload.get("total_amount")
        if total_amount is None and per_capita and guests:
            total_amount = per_capita * (guests + accompany_count)

        record = ReceptionRecord(
            id=None,
            serial_number=serial_number,
            scenario=payload.get("scenario", ""),
            scenario_name=payload.get("scenario_name", ""),
            submitter=payload.get("submitter", "匿名"),
            date=payload.get("date", ""),
            location=payload.get("location", ""),
            org=payload.get("org", ""),
            guests=guests,
            accompany_people=payload.get("accompany_people", ""),
            accompany_count=accompany_count,
            per_capita=per_capita,
            total_amount=total_amount,
            baijiu_price=payload.get("baijiu_price", ""),
            wine_price=payload.get("wine_price", ""),
            gift_per=payload.get("gift_per", ""),
            rooms=payload.get("rooms", ""),
            room_price=payload.get("room_price", ""),
            reason=payload.get("reason", ""),
            nationality=payload.get("nationality", ""),
            fee=payload.get("fee", ""),
            status="pending",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return {
            "id": record.id,
            "serial_number": record.serial_number,
            "message": f"记录已提交，流水号: {record.serial_number}",
            "status": record.status,
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")
    finally:
        session.close()


# 状态码映射（英文 → 中文）
STATUS_LABEL = {
    "pending": "待审核",
    "approved": "已通过",
    "rejected": "已驳回",
}


def _status_label(status):
    """返回中文状态标签，兼容中英文输入"""
    if not status:
        return "待审核"
    if status in STATUS_LABEL:
        return STATUS_LABEL[status]
    # 已经是中文直接返回
    return status


@router.get("/reception-records")
def list_records(
    scenario: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    username: Optional[str] = Query(None, description="过滤指定提交人的记录"),
    limit: int = Query(500, ge=1, le=5000),
):
    """查询提交记录列表，支持按 username 过滤"""
    session = SessionLocal()
    try:
        q = session.query(ReceptionRecord)
        if scenario:
            q = q.filter(ReceptionRecord.scenario == scenario)
        if status:
            q = q.filter(ReceptionRecord.status == status)
        if username:
            q = q.filter(ReceptionRecord.submitter == username)
        records = q.order_by(ReceptionRecord.id.desc()).limit(limit).all()

        return [
            {
                "id": r.id,
                "serial_number": r.serial_number or "",
                "scenario": r.scenario,
                "scenario_name": r.scenario_name,
                "submitter": r.submitter,
                "date": r.date or "",
                "location": r.location or "",
                "org": r.org or "",
                "guests": r.guests or 0,
                "accompany_people": r.accompany_people or "",
                "accompany_count": r.accompany_count or 0,
                "per_capita": r.per_capita or 0,
                "total_amount": r.total_amount or 0,
                "baijiu_price": r.baijiu_price or "",
                "wine_price": r.wine_price or "",
                "gift_per": r.gift_per or "",
                "rooms": r.rooms or "",
                "room_price": r.room_price or "",
                "reason": r.reason or "",
                "nationality": r.nationality or "",
                "fee": r.fee or "",
                "status": _status_label(r.status),
                "ocr_status": r.ocr_status or "pending",
                "review_status": r.review_status or "pending",
                "ocr_file_count": r.ocr_file_count or 0,
                "created_at": r.created_at or "",
                "updated_at": r.updated_at or "",
            }
            for r in records
        ]
    finally:
        session.close()


@router.delete("/reception-records/{record_id}")
def delete_record(record_id: int, request: Request):
    """删除一条提交记录（非管理员只能删除自己的记录）"""
    current_user = get_optional_user(request)
    session = SessionLocal()
    try:
        record = session.query(ReceptionRecord).filter(ReceptionRecord.id == record_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")

        # 权限校验：已登录非 admin 用户只能删除自己的记录
        if current_user and current_user.role != "admin":
            if record.submitter != current_user.username:
                raise HTTPException(status_code=403, detail="无权删除他人记录")

        session.delete(record)
        session.commit()
        return {"message": "记录已删除"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
    finally:
        session.close()
