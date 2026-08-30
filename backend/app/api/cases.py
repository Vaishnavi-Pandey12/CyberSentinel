from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from app.db.mongo import get_database
from app.schemas.case import CaseCreate, CaseResponse, CaseNoteCreate

router = APIRouter(prefix="/cases", tags=["Cases"])

SEED_CASES = [
    {
        "id": "CYB-2026-1024",
        "status": "ACTIVE",
        "summary": "Coordinated cash-out and ATM compromise indicators across the Vijayawada banking corridor.",
        "risk_level": "CRITICAL",
        "complaints": ["C102", "C183", "C201", "C244"],
        "hotspot_ids": ["p104", "p221"],
        "notes": [
            "Patrol coordination requested for the 18:00–23:00 window.",
            "Bank fraud desk notified; preserve terminal audit logs."
        ],
        "timeline": [
            {"time": "14:05", "event": "Complaint C102 linked to repeated withdrawal pattern", "location": "MG Road ATM Cluster"},
            {"time": "15:10", "event": "Prediction model elevated hotspot risk", "location": "Vijayawada"},
            {"time": "15:42", "event": "Operational alert issued to LEA desk", "location": "ATM-104"}
        ]
    },
    {
        "id": "CYB-2026-1029",
        "status": "ACTIVE",
        "summary": "Financial cyber-fraud signals involving Hyderabad ATM locations.",
        "risk_level": "HIGH",
        "complaints": ["C325", "C388", "C401"],
        "hotspot_ids": ["p087", "p176"],
        "notes": ["Review affected account freeze requests."],
        "timeline": [
            {"time": "11:30", "event": "Complaint cluster received", "location": "KPHB Metro ATM"}
        ]
    }
]

async def seed_cases_if_empty():
    db = get_database()
    count = await db.cases.count_documents({})
    if count == 0:
        await db.cases.insert_many(SEED_CASES)

@router.get("/", response_model=List[CaseResponse])
async def get_cases():
    db = get_database()
    await seed_cases_if_empty()
    cases = await db.cases.find({}, {"_id": 0}).to_list(length=100)
    return cases

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case_by_id(case_id: str):
    db = get_database()
    await seed_cases_if_empty()
    case = await db.cases.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case record with ID '{case_id}' was not found."
        )
    return case

@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(case_input: CaseCreate):
    db = get_database()
    existing = await db.cases.find_one({"id": case_input.id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Case with ID '{case_input.id}' already exists."
        )
    case_doc = case_input.model_dump()
    await db.cases.insert_one(case_doc)
    return CaseResponse.model_validate(case_doc)

@router.post("/{case_id}/notes", response_model=CaseResponse)
async def add_case_note(case_id: str, note_input: CaseNoteCreate):
    db = get_database()
    await seed_cases_if_empty()
    result = await db.cases.find_one_and_update(
        {"id": case_id},
        {"$push": {"notes": note_input.note}},
        return_document=True
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case record '{case_id}' not found."
        )
    if "_id" in result:
        del result["_id"]
    return CaseResponse.model_validate(result)

@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(case_id: str, update_data: dict):
    db = get_database()
    await seed_cases_if_empty()
    # Filter out _id or id updates if present
    clean_update = {k: v for k, v in update_data.items() if k not in ["_id", "id"]}
    if not clean_update:
        raise HTTPException(status_code=400, detail="No valid fields provided for update.")
    
    result = await db.cases.find_one_and_update(
        {"id": case_id},
        {"$set": clean_update},
        return_document=True
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case record '{case_id}' not found."
        )
    if "_id" in result:
        del result["_id"]
    return CaseResponse.model_validate(result)
