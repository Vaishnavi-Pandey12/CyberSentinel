import os
import joblib
import numpy as np
import pandas as pd
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:
    from src.spatial_dbscan import cluster_interdiction_zones
except ImportError:
    from spatial_dbscan import cluster_interdiction_zones

# 1. Define Request / Response Schemas (API Contract)
class LocationCandidate(BaseModel):
    location_id: str
    latitude: float
    longitude: float
    log_transaction_amount: float
    log_account_balance: float
    recent_txn_count: int
    recent_withdrawal_count: int
    withdrawal_ratio: float
    distance_to_recent_withdrawal_km: float
    dist_from_last_txn_km: float
    minutes_since_last_txn: float
    withdrawals_past_1h: int
    withdrawals_past_24h: int
    location_density_30d: int
    historical_location_risk: float
    login_attempts: int
    transaction_duration: float
    customer_age: int
    hour_sin: float
    hour_cos: float
    day_sin: float
    day_cos: float
    is_weekend: int
    location_numeric_id: int
    crime_cat_routine_transaction: int
    crime_cat_suspicious_cash_withdrawal: int
    crime_cat_unusual_online_activity: int
    crime_cat_high_value_transfer: int

class PredictRequest(BaseModel):
    candidates: List[LocationCandidate]
    predicted_window: Optional[str] = "3h"

class PredictionResult(BaseModel):
    prediction_id: str
    location_id: str
    risk_score: float
    risk_level: str
    predicted_window: str
    rank: int
    top_factors: List[str]
    model_version: str
    cluster_id: Optional[str] = "UNCATEGORIZED"
    is_interdiction_zone: bool = False

class PredictResponse(BaseModel):
    status: str
    count: int
    predictions: List[PredictionResult]

# 2. Initialize FastAPI and Load Trained Isolation Forest Artifact
app = FastAPI(title="Cybercrime Withdrawal Hotspot Risk Prediction Service")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "model.pkl")

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model artifact not found at {MODEL_PATH}. Run train.py first.")

artifact = joblib.load(MODEL_PATH)
iso_forest = artifact["model"]
expected_features = artifact["feature_names"]
model_version = artifact.get("model_version", "iso_forest_v1")

# Baseline profile for explaining anomalies
REFERENCE_MEANS = {
    "dist_from_last_txn_km": 150.0,
    "distance_to_recent_withdrawal_km": 200.0,
    "login_attempts": 1.5,
    "historical_location_risk": 0.35,
    "recent_withdrawal_count": 1.0,
    "minutes_since_last_txn": 300.0
}

def calibrate_anomaly_to_risk(raw_score: float, k: float = 40.0) -> float:
    """
    Transforms Isolation Forest decision_function score (negative = anomalous)
    into a calibrated [0.0, 1.0] risk score using a sigmoid function.
    """
    score = 1.0 / (1.0 + np.exp(k * raw_score))
    return float(np.clip(score, 0.0, 1.0))

def get_risk_level(risk_score: float) -> str:
    """Map risk score to discrete operational tiers."""
    if risk_score >= 0.85:
        return "CRITICAL"
    elif risk_score >= 0.70:
        return "HIGH"
    elif risk_score >= 0.50:
        return "MEDIUM"
    return "LOW"

def extract_top_factors(row: pd.Series) -> List[str]:
    """Identifies the top contributing anomalous factors for investigator alerts."""
    factors = []
    if row.get("dist_from_last_txn_km", 0) > REFERENCE_MEANS["dist_from_last_txn_km"]:
        factors.append("large_distance_from_last_transaction")
    if row.get("login_attempts", 0) > REFERENCE_MEANS["login_attempts"]:
        factors.append("repeated_login_failures")
    if row.get("historical_location_risk", 0) > REFERENCE_MEANS["historical_location_risk"]:
        factors.append("high_historical_location_risk")
    if row.get("recent_withdrawal_count", 0) > REFERENCE_MEANS["recent_withdrawal_count"]:
        factors.append("frequent_recent_withdrawals")

    if not factors:
        factors = ["routine_activity_profile", "baseline_pattern"]
    return factors[:3]

# 3. Prediction Endpoint
@app.post("/predict", response_model=PredictResponse)
def predict_hotspots(payload: PredictRequest):
    if not payload.candidates:
        raise HTTPException(status_code=400, detail="Candidate list is empty.")

    # Convert candidate payload into DataFrame
    candidate_dicts = [c.dict() for c in payload.candidates]
    df_candidates = pd.DataFrame(candidate_dicts)

    # Run Spatial DBSCAN Clustering to tag locations into Interdiction Zones
    try:
        df_clustered = cluster_interdiction_zones(df_candidates, eps_km=2.0, min_samples=2)
    except Exception:
        df_clustered = df_candidates.copy()
        df_clustered['cluster_id'] = -1
        df_clustered['is_interdiction_zone'] = 0

    # Align feature matrix with the Isolation Forest's training columns
    X_input = df_candidates.reindex(columns=expected_features, fill_value=0)

    # Compute raw anomaly score (lower/negative = higher anomaly)
    raw_anomaly_scores = iso_forest.decision_function(X_input)

    # Compute risk score, level, and factors per candidate
    scored_candidates = []
    for idx, row in df_candidates.iterrows():
        raw_score = raw_anomaly_scores[idx]
        risk_score = calibrate_anomaly_to_risk(raw_score)
        risk_level = get_risk_level(risk_score)
        top_factors = extract_top_factors(row)

        cid = str(df_clustered.loc[idx, 'cluster_id']) if 'cluster_id' in df_clustered.columns else "UNCATEGORIZED"
        is_interdiction = bool(df_clustered.loc[idx, 'is_interdiction_zone'] == 1) if 'is_interdiction_zone' in df_clustered.columns else False

        scored_candidates.append({
            "location_id": row["location_id"],
            "risk_score": round(risk_score, 4),
            "risk_level": risk_level,
            "predicted_window": payload.predicted_window,
            "top_factors": top_factors,
            "model_version": model_version,
            "cluster_id": f"CLUSTER_{cid}" if cid != "-1" and cid != "UNCATEGORIZED" else "UNCATEGORIZED",
            "is_interdiction_zone": is_interdiction
        })

    # Sort descending by risk score to rank hotspots (Rank 1 = highest risk)
    scored_candidates.sort(key=lambda x: x["risk_score"], reverse=True)

    # Build final response with prediction IDs and ranks
    predictions = [
        PredictionResult(
            prediction_id=f"pred_{rank_idx:03d}",
            rank=rank_idx,
            **candidate
        )
        for rank_idx, candidate in enumerate(scored_candidates, start=1)
    ]

    return PredictResponse(
        status="success",
        count=len(predictions),
        predictions=predictions
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
 