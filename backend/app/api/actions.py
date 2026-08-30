from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import hashlib
import json
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from app.db.mongo import get_database

router = APIRouter(prefix="/action", tags=["Actions & Ledger"])

class FreezeRequest(BaseModel):
    node_id: str
    officer_id: str
    reason: str

def generate_sha256_hash(data_string: str) -> str:
    """Helper function to generate a SHA256 cryptographic hash."""
    return hashlib.sha256(data_string.encode('utf-8')).hexdigest()

def get_db(request: Request):
    if hasattr(request.app, "mongodb") and request.app.mongodb is not None:
        return request.app.mongodb
    return get_database()

@router.post("/freeze")
@router.post("/api/action/freeze")
async def freeze_account(request_body: FreezeRequest, request: Request):
    db = get_db(request)
    nodes_col = db["nodes"]
    audit_col = db["audit_logs"]

    # 1. Flexible target ID lookup (ObjectId or string ID)
    if ObjectId.is_valid(request_body.node_id):
        target_query = {"$or": [{"_id": ObjectId(request_body.node_id)}, {"_id": request_body.node_id}, {"id": request_body.node_id}]}
    else:
        target_query = {"$or": [{"_id": request_body.node_id}, {"id": request_body.node_id}]}

    node = await nodes_col.find_one(target_query)
    
    # Baseline seed fallback if node is absent
    if not node:
        seed_doc = {"_id": request_body.node_id, "type": "MULE", "status": "ACTIVE", "riskScore": 85}
        await nodes_col.insert_one(seed_doc)
        node = seed_doc

    if node.get("status") == "FROZEN":
        raise HTTPException(status_code=400, detail="Account is already frozen")

    # 2. Update the Node status in the database
    target_id_val = str(node.get("_id", request_body.node_id))
    await nodes_col.update_one(
        target_query,
        {"$set": {"status": "FROZEN"}}
    )

    # 3. Construct the Action Data for the ledger
    action_data = {
        "action": "FREEZE_INITIATED",
        "target_node": target_id_val,
        "officer_id": request_body.officer_id,
        "reason": request_body.reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # 4. Fetch the previous block's hash to maintain the chain (sorted by _id descending)
    last_log = await audit_col.find_one({}, sort=[("_id", -1)])
    
    if last_log and last_log.get("currentHash"):
        previous_hash = last_log["currentHash"]
    else:
        # Genesis Block: If the log is empty, start with a known seed
        previous_hash = generate_sha256_hash("GENESIS_BLOCK_SEED")

    # 5. Generate the Current Hash = SHA256(previousHash + stringified actionData)
    data_to_hash = previous_hash + json.dumps(action_data, sort_keys=True)
    current_hash = generate_sha256_hash(data_to_hash)

    # 6. Save the new immutable record to the Audit Log
    new_audit_entry = {
        "action": action_data["action"],
        "targetNodeId": target_id_val,
        "actionData": action_data,
        "previousHash": previous_hash,
        "currentHash": current_hash,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await audit_col.insert_one(new_audit_entry)

    return {
        "status": "success",
        "message": f"Account {request_body.node_id} successfully frozen.",
        "audit_receipt": {
            "transaction_hash": current_hash,
            "previous_hash": previous_hash
        }
    }

@router.get("/audit-logs")
@router.get("/api/action/audit-logs")
async def get_audit_logs(request: Request):
    """Fetches the most recent cryptographic ledger entries for the terminal."""
    try:
        db = get_db(request)
        audit_col = db["audit_logs"]
        logs = await audit_col.find().sort([("_id", -1)]).to_list(length=20)
        return [
            {
                "id": str(log.get("_id")),
                "action": log.get("action", "FREEZE_INITIATED"),
                "targetNodeId": str(log.get("targetNodeId", "")),
                "previousHash": log.get("previousHash", ""),
                "currentHash": log.get("currentHash", ""),
                "timestamp": str(log.get("createdAt") or datetime.now(timezone.utc).isoformat())
            }
            for log in logs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

