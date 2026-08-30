from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime, timezone
from app.db.mongo import get_database
from app.schemas.complaint import ComplaintCreate, ComplaintResponse

router = APIRouter(prefix="/complaints", tags=["Complaints"])

SEED_COMPLAINTS = [
    {"complaint_id": "C102", "crime_category": "Financial Cyber Fraud", "region": "Vijayawada", "account_number": "XXXX-1234", "amount": 45000.0, "timestamp": datetime.now(timezone.utc)},
    {"complaint_id": "C183", "crime_category": "ATM Skimming", "region": "Vijayawada", "account_number": "XXXX-5678", "amount": 25000.0, "timestamp": datetime.now(timezone.utc)},
    {"complaint_id": "C201", "crime_category": "Financial Cyber Fraud", "region": "Vijayawada", "account_number": "XXXX-9012", "amount": 80000.0, "timestamp": datetime.now(timezone.utc)},
    {"complaint_id": "C244", "crime_category": "ATM Skimming", "region": "Vijayawada", "account_number": "XXXX-3456", "amount": 15000.0, "timestamp": datetime.now(timezone.utc)},
    {"complaint_id": "C325", "crime_category": "Financial Cyber Fraud", "region": "Hyderabad", "account_number": "XXXX-7890", "amount": 120000.0, "timestamp": datetime.now(timezone.utc)},
    {"complaint_id": "C388", "crime_category": "Financial Cyber Fraud", "region": "Hyderabad", "account_number": "XXXX-2345", "amount": 60000.0, "timestamp": datetime.now(timezone.utc)},
    {"complaint_id": "C401", "crime_category": "Account Takeover", "region": "Hyderabad", "account_number": "XXXX-6789", "amount": 35000.0, "timestamp": datetime.now(timezone.utc)},
]

async def seed_complaints_if_empty():
    db = get_database()
    count = await db.complaints.count_documents({})
    if count == 0:
        await db.complaints.insert_many(SEED_COMPLAINTS)

@router.get("/", response_model=List[ComplaintResponse])
async def get_complaints(
    region: Optional[str] = Query(default=None),
    crime_category: Optional[str] = Query(default=None)
):
    db = get_database()
    await seed_complaints_if_empty()
    query = {}
    if region:
        query["region"] = region
    if crime_category:
        query["crime_category"] = crime_category

    complaints = await db.complaints.find(query, {"_id": 0}).to_list(length=100)
    return [ComplaintResponse.model_validate(c) for c in complaints]

@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint_by_id(complaint_id: str):
    db = get_database()
    await seed_complaints_if_empty()
    complaint = await db.complaints.find_one({"complaint_id": complaint_id}, {"_id": 0})
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint record '{complaint_id}' was not found."
        )
    return ComplaintResponse.model_validate(complaint)

@router.post("/", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def create_complaint(complaint_input: ComplaintCreate):
    db = get_database()
    complaint_doc = complaint_input.model_dump()
    if not complaint_doc.get("timestamp"):
        complaint_doc["timestamp"] = datetime.now(timezone.utc)
    
    await db.complaints.insert_one(complaint_doc)
    if "_id" in complaint_doc:
        del complaint_doc["_id"]
    return ComplaintResponse.model_validate(complaint_doc)
