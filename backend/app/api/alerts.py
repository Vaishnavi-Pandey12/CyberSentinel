from fastapi import APIRouter, Request, HTTPException, status
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId
from app.db.mongo import get_database
from app.schemas.alert import AlertCreate, AlertAcknowledge

router = APIRouter(prefix="/alerts", tags=["Alerts"])

SEED_ALERTS = [
    {"id": "ALT-104", "prediction_id": "p104", "riskScore": 95.0, "risk_score": 95.0, "severity": "CRITICAL", "status": "NEW", "created_at": "2026-08-30T15:42:00Z"},
    {"id": "ALT-221", "prediction_id": "p221", "riskScore": 92.0, "risk_score": 92.0, "severity": "CRITICAL", "status": "ACKNOWLEDGED", "created_at": "2026-08-30T14:10:00Z", "acknowledged_at": "2026-08-30T14:30:00Z"},
    {"id": "ALT-087", "prediction_id": "p087", "riskScore": 78.0, "risk_score": 78.0, "severity": "HIGH", "status": "NEW", "created_at": "2026-08-30T12:05:00Z"},
    {"id": "ALT-309", "prediction_id": "p309", "riskScore": 55.0, "risk_score": 55.0, "severity": "MEDIUM", "status": "NEW", "created_at": "2026-08-30T09:32:00Z"},
]

def get_db(request: Request):
    if hasattr(request.app, "mongodb") and request.app.mongodb is not None:
        return request.app.mongodb
    return get_database()

def build_alert_query(alert_id: str):
    if ObjectId.is_valid(alert_id):
        return {"$or": [{"_id": ObjectId(alert_id)}, {"id": alert_id}]}
    return {"id": alert_id}

async def seed_alerts_if_empty(db):
    count = await db["alerts"].count_documents({})
    if count == 0:
        await db["alerts"].insert_many(SEED_ALERTS)

@router.get("/")
async def get_alerts(request: Request):
    db = get_db(request)
    await seed_alerts_if_empty(db)
    alerts = await db["alerts"].find().to_list(length=100)
    for a in alerts:
        if "_id" in a:
            a["_id"] = str(a["_id"])
        if "id" not in a:
            a["id"] = a["_id"]
        # Ensure riskScore & risk_score are populated if missing
        if "riskScore" not in a and "risk_score" not in a:
            sev = a.get("severity", "MEDIUM").upper()
            score = 95.0 if sev == "CRITICAL" else (82.0 if sev == "HIGH" else 58.0)
            a["riskScore"] = score
            a["risk_score"] = score
        elif "riskScore" in a and "risk_score" not in a:
            a["risk_score"] = a["riskScore"]
        elif "risk_score" in a and "riskScore" not in a:
            a["riskScore"] = a["risk_score"]
    return {"status": "success", "count": len(alerts), "data": alerts}

@router.post("/{alert_id}/acknowledge")
@router.patch("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, request: Request):
    db = get_db(request)
    await seed_alerts_if_empty(db)
    now_iso = datetime.now(timezone.utc).isoformat()
    
    result = await db["alerts"].find_one_and_update(
        build_alert_query(alert_id),
        {"$set": {"status": "ACKNOWLEDGED", "acknowledged_at": now_iso}},
        return_document=True
    )
    if not result:
        update_res = await db["alerts"].update_one(
            build_alert_query(alert_id),
            {"$set": {"status": "ACKNOWLEDGED", "acknowledged_at": now_iso}}
        )
        if update_res.matched_count == 0:
            await db["alerts"].update_one(
                {"id": alert_id},
                {"$set": {"id": alert_id, "status": "ACKNOWLEDGED", "acknowledged_at": now_iso}},
                upsert=True
            )
        result = await db["alerts"].find_one(build_alert_query(alert_id))
        
    if result and "_id" in result:
        result["_id"] = str(result["_id"])
    return {"message": "Alert acknowledged successfully", "status": "success", "data": result}

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_alert(alert: AlertCreate, request: Request):
    db = get_db(request)
    now_iso = datetime.now(timezone.utc).isoformat()
    alert_doc = alert.model_dump()
    if not alert_doc.get("id"):
        alert_doc["id"] = f"ALT-{int(datetime.now().timestamp())}"
    alert_doc["created_at"] = now_iso
    await db["alerts"].insert_one(alert_doc)
    if "_id" in alert_doc:
        alert_doc["_id"] = str(alert_doc["_id"])
    return {"status": "success", "data": alert_doc}