"""招待费提交记录 API"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from .models_db import ReceptionRecord, SessionLocal

router = APIRouter()


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


@router.get("/reception-records")
def list_records(
    scenario: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
):
    """查询提交记录列表"""
    session = SessionLocal()
    try:
        q = session.query(ReceptionRecord)
        if scenario:
            q = q.filter(ReceptionRecord.scenario == scenario)
        if status:
            q = q.filter(ReceptionRecord.status == status)
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
                "status": r.status or "pending",
                "created_at": r.created_at or "",
                "updated_at": r.updated_at or "",
            }
            for r in records
        ]
    finally:
        session.close()


@router.delete("/reception-records/{record_id}")
def delete_record(record_id: int):
    """删除一条提交记录"""
    session = SessionLocal()
    try:
        record = session.query(ReceptionRecord).filter(ReceptionRecord.id == record_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
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
