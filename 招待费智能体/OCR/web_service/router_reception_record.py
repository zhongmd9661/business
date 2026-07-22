"""招待费提交记录 API 路由"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from .models_db import ReceptionRecord, get_db

router = APIRouter()

SCENARIO_NAMES = {
    "A": "商务招待",
    "B": "外事招待",
    "C": "其他公务招待",
    "D": "内部业务招待",
    "E": "工作餐",
    "F": "党政军机关",
}


@router.post("/api/reception-records", summary="提交招待费记录")
def submit_record(record: dict, db=Depends(get_db)):
    """提交一条招待费记录"""
    scenario = record.get("scenario", "A")
    scenario_name = SCENARIO_NAMES.get(scenario, "未知场景")

    # 计算各项费用
    guests = int(record.get("guests", 0))
    per_capita = float(record.get("perCapita", 0))
    meal_total = guests * per_capita

    # 酒水费用：白酒按 0.5 瓶/人，红酒按 0.75 瓶/人估算
    baijiu_price = float(record.get("baijiuPrice", 0))
    wine_price = float(record.get("winePrice", 0))
    alcohol_total = (baijiu_price * 0.5 + wine_price * 0.75) * guests if (baijiu_price or wine_price) else 0

    # 纪念品
    gift_per = float(record.get("giftPer", 0))
    gift_total = gift_per * guests

    # 住宿
    rooms = int(record.get("rooms", 0))
    room_price = float(record.get("roomPrice", 0))
    room_total = rooms * room_price

    total_amount = meal_total + alcohol_total + gift_total + room_total

    new_record = ReceptionRecord(
        scenario=scenario,
        scenario_name=scenario_name,
        date=record.get("date", ""),
        location=record.get("location", ""),
        org=record.get("org", ""),
        guests=guests,
        accompany_count=int(record.get("accompanyCount", 0)),
        per_capita=per_capita,
        meal_total=meal_total,
        alcohol_total=alcohol_total,
        gift_total=gift_total,
        room_total=room_total,
        total_amount=total_amount,
        reason=record.get("reason", ""),
        submitter=record.get("submitter", "匿名"),
        status="待审核",
        created_at=datetime.now().isoformat(),
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return {
        "id": new_record.id,
        "status": "success",
        "message": f"场景 {scenario} 记录已提交，总金额 ¥{total_amount:.2f}",
    }


@router.get("/api/reception-records", summary="查询招待费记录")
def list_records(
    scenario: str = Query(None, description="按场景筛选"),
    status: str = Query(None, description="按状态筛选"),
    limit: int = Query(50, ge=1, le=500, description="返回条数"),
    db=Depends(get_db),
):
    """查询招待费提交记录列表"""
    query = db.query(ReceptionRecord)

    if scenario:
        query = query.filter(ReceptionRecord.scenario == scenario)
    if status:
        query = query.filter(ReceptionRecord.status == status)

    records = query.order_by(ReceptionRecord.created_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "scenario": r.scenario,
            "scenario_name": r.scenario_name,
            "date": r.date,
            "location": r.location,
            "org": r.org,
            "guests": r.guests,
            "accompany_count": r.accompany_count,
            "per_capita": r.per_capita,
            "meal_total": r.meal_total,
            "alcohol_total": r.alcohol_total,
            "gift_total": r.gift_total,
            "room_total": r.room_total,
            "total_amount": r.total_amount,
            "reason": r.reason,
            "submitter": r.submitter,
            "status": r.status,
            "remark": r.remark,
            "created_at": r.created_at,
        }
        for r in records
    ]


@router.get("/api/reception-records/{record_id}", summary="查询单条记录详情")
def get_record(record_id: int, db=Depends(get_db)):
    """查询单条记录详情"""
    record = db.query(ReceptionRecord).filter(ReceptionRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "记录不存在")

    return {
        "id": record.id,
        "scenario": record.scenario,
        "scenario_name": record.scenario_name,
        "date": record.date,
        "location": record.location,
        "org": record.org,
        "guests": record.guests,
        "accompany_count": record.accompany_count,
        "per_capita": record.per_capita,
        "meal_total": record.meal_total,
        "alcohol_total": record.alcohol_total,
        "gift_total": record.gift_total,
        "room_total": record.room_total,
        "total_amount": record.total_amount,
        "reason": record.reason,
        "submitter": record.submitter,
        "status": record.status,
        "remark": record.remark,
        "created_at": record.created_at,
    }


@router.delete("/api/reception-records/{record_id}", summary="删除记录")
def delete_record(record_id: int, db=Depends(get_db)):
    """删除一条记录"""
    record = db.query(ReceptionRecord).filter(ReceptionRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "记录不存在")

    db.delete(record)
    db.commit()
    return {"status": "success", "message": "记录已删除"}


@router.put("/api/reception-records/{record_id}", summary="更新记录状态")
def update_record_status(record_id: int, update: dict, db=Depends(get_db)):
    """更新记录状态或备注"""
    record = db.query(ReceptionRecord).filter(ReceptionRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "记录不存在")

    if "status" in update:
        record.status = update["status"]
    if "remark" in update:
        record.remark = update["remark"]

    db.commit()
    return {"status": "success", "message": "记录已更新"}
