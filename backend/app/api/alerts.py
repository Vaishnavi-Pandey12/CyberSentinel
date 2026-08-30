from fastapi import APIRouter, HTTPException, status
from typing import Optional
from datetime import datetime, timezone
from app.db.mongo import get_database
from app.schemas.alert import AlertCreate, AlertAcknowledge

router = APIRouter(prefix="/alerts", tags=["Alerts"])

SEED_ALERTS = [
    {"id": "ALT-104", "prediction_id": "p104", "severity": "CRITICAL", "status": "NEW", "created_at": "2026-08-30T15:42:00Z"},
    {"id": "ALT-221", "prediction_id": "p221", "severity": "CRITICAL", "status": "ACKNOWLEDGED", "created_at": "2026-08-30T14:10:00Z", "acknowledged_at": "2026-08-30T14:30:00Z"},
    {"id": "ALT-087", "prediction_id": "p087", "severity": "HIGH", "status": "NEW", "created_at": "2026-08-30T12:05:00Z"},
    {"id": "ALT-309", "prediction_id": "p309", "severity": "MEDIUM", "status": "NEW", "created_at": "2026-08-30T09:32:00Z"},
]

async def seed_alerts_if_empty():
    db = get_database()
    count = await db.alerts.count_documents({})
    if count == 0:
        await db.alerts.insert_many(SEED_ALERTS)

@router.get("/")
async def get_alerts():
    db = get_database()
    await seed_alerts_if_empty()
    alerts = await db.alerts.find({}, {"_id": 0}).to_list(length=100)
    return {"status": "success", "count": len(alerts), "data": alerts}

@router.post("/{alert_id}/acknowledge")
@router.patch("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, payload: Optional[AlertAcknowledge] = None):
    db = get_database()
    await seed_alerts_if_empty()
    now_iso = datetime.now(timezone.utc).isoformat()
    
    result = await db.alerts.find_one_and_update(
        {"id": alert_id},
        {"$set": {"status": "ACKNOWLEDGED", "acknowledged_at": now_iso}},
        return_document=True
    )
    if not result:
        # Upsert if alert wasn't already in DB
        await db.alerts.update_one(
            {"id": alert_id},
            {"$set": {"id": alert_id, "status": "ACKNOWLEDGED", "acknowledged_at": now_iso}},
            upsert=True
        )
        result = await db.alerts.find_one({"id": alert_id}, {"_id": 0})
        
    if "_id" in result:
        del result["_id"]
    return {"status": "success", "data": result}

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_alert(alert: AlertCreate):
    db = get_database()
    now_iso = datetime.now(timezone.utc).isoformat()
    alert_doc = alert.model_dump()
    if not alert_doc.get("id"):
        alert_doc["id"] = f"ALT-{int(datetime.now().timestamp())}"
    alert_doc["created_at"] = now_iso
    await db.alerts.insert_one(alert_doc)
    if "_id" in alert_doc:
        del alert_doc["_id"]
    return {"status": "success", "data": alert_doc}