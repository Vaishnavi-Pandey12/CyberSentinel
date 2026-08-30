from fastapi import APIRouter, Request, HTTPException, status
from typing import List, Optional, Union
from datetime import datetime, timezone
from bson import ObjectId
from app.db.mongo import get_database

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

def get_db(request: Request):
    if hasattr(request.app, "mongodb") and request.app.mongodb is not None:
        return request.app.mongodb
    return get_database()

def build_id_query(case_id: str):
    if ObjectId.is_valid(case_id):
        return {"$or": [{"_id": ObjectId(case_id)}, {"id": case_id}]}
    return {"id": case_id}

async def seed_cases_if_empty(db):
    count = await db["cases"].count_documents({})
    if count == 0:
        await db["cases"].insert_many(SEED_CASES)

@router.get("/")
async def get_cases(request: Request):
    db = get_db(request)
    await seed_cases_if_empty(db)
    cases = await db["cases"].find().to_list(length=100)
    for case in cases:
        if "_id" in case:
            case["_id"] = str(case["_id"])
        if "id" not in case:
            case["id"] = case["_id"]
    return cases

@router.get("/{case_id}")
async def get_case(case_id: str, request: Request):
    db = get_db(request)
    await seed_cases_if_empty(db)
    case = await db["cases"].find_one(build_id_query(case_id))
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    if "_id" in case:
        case["_id"] = str(case["_id"])
    if "id" not in case:
        case["id"] = case["_id"]
    return case

@router.post("/")
async def create_case(request: Request, case_data: dict):
    db = get_db(request)
    if "created_at" not in case_data:
        case_data["created_at"] = datetime.now(timezone.utc).isoformat()
    if "status" not in case_data:
        case_data["status"] = "ACTIVE"
    
    result = await db["cases"].insert_one(case_data)
    inserted_id = str(result.inserted_id)
    return {"message": "Case created", "id": case_data.get("id", inserted_id), "_id": inserted_id}

@router.patch("/{case_id}")
async def update_case(case_id: str, request: Request, update_data: dict):
    db = get_db(request)
    await seed_cases_if_empty(db)
    clean_update = {k: v for k, v in update_data.items() if k not in ["_id", "id"]}
    if not clean_update:
        raise HTTPException(status_code=400, detail="No valid fields provided for update")

    result = await db["cases"].update_one(
        build_id_query(case_id), {"$set": clean_update}
    )
    if result.matched_count == 0 and result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Case not found or not updated")
    return {"message": "Case updated successfully"}

@router.post("/{case_id}/notes")
async def add_case_note(case_id: str, request: Request, note_payload: Union[dict, str]):
    db = get_db(request)
    await seed_cases_if_empty(db)
    
    note_text = ""
    if isinstance(note_payload, dict):
        note_text = note_payload.get("note") or note_payload.get("text") or str(note_payload)
    else:
        note_text = str(note_payload)

    result = await db["cases"].update_one(
        build_id_query(case_id), {"$push": {"notes": note_text}}
    )
    if result.matched_count == 0 and result.modified_count == 0:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
        
    updated_case = await db["cases"].find_one(build_id_query(case_id))
    if updated_case and "_id" in updated_case:
        updated_case["_id"] = str(updated_case["_id"])
    return updated_case or {"message": "Note added"}
