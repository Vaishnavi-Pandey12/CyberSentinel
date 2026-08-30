from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone

class NodeModel(BaseModel):
    """Node Collection Schema (Victim, Mule/Suspect, ATM, Device)."""
    id: Optional[str] = Field(None, alias="_id")
    type: str  # VICTIM, MULE, ATM, DEVICE
    riskScore: float = 0.0
    status: str = "ACTIVE"  # ACTIVE, FROZEN, INVESTIGATING
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EdgeModel(BaseModel):
    """Edge Collection Schema (Money transfers, withdrawals, logins)."""
    id: Optional[str] = Field(None, alias="_id")
    source: str  # Source Node ID (e.g. Victim Account)
    target: str  # Target Node ID (e.g. Mule Account or ATM)
    type: str  # TRANSFER, WITHDRAWAL, LOGIN
    amount: Optional[float] = 0.0
    weight: Optional[float] = 1.0

class AuditLogModel(BaseModel):
    """AuditLog Collection Schema (Immutable SHA-256 Blockchain Ledger)."""
    id: Optional[str] = Field(None, alias="_id")
    action: str  # FREEZE_INITIATED
    targetNodeId: str
    actionData: Dict[str, Any]
    previousHash: str
    currentHash: str
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
