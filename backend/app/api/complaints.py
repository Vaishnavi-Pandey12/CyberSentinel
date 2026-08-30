from fastapi import APIRouter, Request, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from app.db.mongo import get_database

router = APIRouter(prefix="/complaints", tags=["Complaints"])

SEED_COMPLAINTS = [
    {"complaint_id": "C102", "crime_category": "Financial Cyber Fraud", "region": "Vijayawada", "account_number": "XXXX-1234", "amount": 45000.0, "timestamp": datetime.now(timezone.utc).isoformat()},
    {"complaint_id": "C183", "crime_category": "ATM Skimming", "region": "Vijayawada", "account_number": "XXXX-5678", "amount": 25000.0, "timestamp": datetime.now(timezone.utc).isoformat()},
    {"complaint_id": "C201", "crime_category": "Financial Cyber Fraud", "region": "Vijayawada", "account_number": "XXXX-9012", "amount": 80000.0, "timestamp": datetime.now(timezone.utc).isoformat()},
    {"complaint_id": "C244", "crime_category": "ATM Skimming", "region": "Vijayawada", "account_number": "XXXX-3456", "amount": 15000.0, "timestamp": datetime.now(timezone.utc).isoformat()},
    {"complaint_id": "C325", "crime_category": "Financial Cyber Fraud", "region": "Hyderabad", "account_number": "XXXX-7890", "amount": 120000.0, "timestamp": datetime.now(timezone.utc).isoformat()},
    {"complaint_id": "C388", "crime_category": "Financial Cyber Fraud", "region": "Hyderabad", "account_number": "XXXX-2345", "amount": 60000.0, "timestamp": datetime.now(timezone.utc).isoformat()},
    {"complaint_id": "C401", "crime_category": "Account Takeover", "region": "Hyderabad", "account_number": "XXXX-6789", "amount": 35000.0, "timestamp": datetime.now(timezone.utc).isoformat()},
]

def get_db(request: Request):
    if hasattr(request.app, "mongodb") and request.app.mongodb is not None:
        return request.app.mongodb
    return get_database()

def build_id_query(complaint_id: str):
    if ObjectId.is_valid(complaint_id):
        return {"$or": [{"_id": ObjectId(complaint_id)}, {"complaint_id": complaint_id}, {"id": complaint_id}]}
    return {"$or": [{"complaint_id": complaint_id}, {"id": complaint_id}]}

async def seed_complaints_if_empty(db):
    count = await db["complaints"].count_documents({})
    if count == 0:
        await db["complaints"].insert_many(SEED_COMPLAINTS)

@router.get("/")
async def get_complaints(
    request: Request,
    region: Optional[str] = Query(default=None),
    crime_category: Optional[str] = Query(default=None)
):
    db = get_db(request)
    await seed_complaints_if_empty(db)
    query = {}
    if region:
        query["region"] = region
    if crime_category:
        query["crime_category"] = crime_category

    complaints = await db["complaints"].find(query).to_list(length=100)
    for c in complaints:
        if "_id" in c:
            c["_id"] = str(c["_id"])
        if "id" not in c:
            c["id"] = c.get("complaint_id", c["_id"])
    return complaints

@router.get("/{complaint_id}")
async def get_complaint(complaint_id: str, request: Request):
    db = get_db(request)
    await seed_complaints_if_empty(db)
    complaint = await db["complaints"].find_one(build_id_query(complaint_id))
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if "_id" in complaint:
        complaint["_id"] = str(complaint["_id"])
    return complaint

@router.post("/")
async def create_complaint(request: Request, complaint_data: dict):
    db = get_db(request)
    if "reported_at" not in complaint_data and "timestamp" not in complaint_data:
        complaint_data["reported_at"] = datetime.now(timezone.utc).isoformat()
    result = await db["complaints"].insert_one(complaint_data)
    inserted_id = str(result.inserted_id)
    return {"message": "Complaint logged", "id": complaint_data.get("complaint_id", inserted_id), "_id": inserted_id}
