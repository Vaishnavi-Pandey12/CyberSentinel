import math
# pyrefly: ignore [missing-import]
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional
from app.config import settings
from app.db.mongo import get_database
from app.schemas.prediction import PredictionResponse
from app.auth.dependencies import get_current_user
from app.schemas.auth import TokenData

router = APIRouter(prefix="/predictions", tags=["Predictions"])

@router.get("/", response_model=List[PredictionResponse])
async def get_predictions(
    region: Optional[str] = Query(default=None, description="Filter by geographic region"),
    crime_category: Optional[str] = Query(default=None, description="Filter by crime category"),
    predicted_window: Optional[str] = Query(default=None, description="Filter by forecast time window"),
    risk_level: Optional[str] = Query(default=None, description="Filter by risk severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    current_user: TokenData = Depends(get_current_user)
):
    db = get_database()
    
    # 1. Build MongoDB match query
    query = {}
    if region:
        query["region"] = region
    if crime_category:
        query["crime_category"] = crime_category
    if predicted_window:
        query["predicted_window"] = predicted_window
    if risk_level:
        query["risk_level"] = risk_level.upper()

    # 2. Fetch predictions
    predictions = await db.predictions.find(query, {"_id": 0}).to_list(length=200)

    # 3. Enrich prediction data with location coordinates and metadata if missing
    locations_cache = {}
    enriched_predictions = []
    
    for p in predictions:
        loc_id = p.get("location_id")
        if loc_id and (p.get("latitude") is None or p.get("longitude") is None or not p.get("location_name")):
            if loc_id not in locations_cache:
                loc_doc = await db.locations.find_one({"location_id": loc_id}, {"_id": 0})
                locations_cache[loc_id] = loc_doc or {}
            
            loc_data = locations_cache[loc_id]
            if loc_data:
                if not p.get("location_name"):
                    p["location_name"] = loc_data.get("location_name", loc_id)
                if not p.get("region") and loc_data.get("region"):
                    p["region"] = loc_data.get("region")
                
                geom = loc_data.get("geometry", {})
                coords = geom.get("coordinates", [])
                if len(coords) == 2:
                    # GeoJSON is [longitude, latitude]
                    if p.get("longitude") is None:
                        p["longitude"] = coords[0]
                    if p.get("latitude") is None:
                        p["latitude"] = coords[1]
                        
        enriched_predictions.append(PredictionResponse.model_validate(p))

    return enriched_predictions

@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction_by_id(
    prediction_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    db = get_database()
    
    # 1. Fetch prediction by ID
    prediction = await db.predictions.find_one({"id": prediction_id}, {"_id": 0})
    if not prediction:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction with ID '{prediction_id}' was not found"
        )

    # 2. Enrich with location data if missing
    loc_id = prediction.get("location_id")
    if loc_id and (prediction.get("latitude") is None or prediction.get("longitude") is None or not prediction.get("location_name")):
        loc_data = await db.locations.find_one({"location_id": loc_id}, {"_id": 0})
        if loc_data:
            if not prediction.get("location_name"):
                prediction["location_name"] = loc_data.get("location_name", loc_id)
            if not prediction.get("region") and loc_data.get("region"):
                prediction["region"] = loc_data.get("region")
            geom = loc_data.get("geometry", {})
            coords = geom.get("coordinates", [])
            if len(coords) == 2:
                if prediction.get("longitude") is None:
                    prediction["longitude"] = coords[0]
                if prediction.get("latitude") is None:
                    prediction["latitude"] = coords[1]

    return PredictionResponse.model_validate(prediction)


@router.post("/predict-live", response_model=List[PredictionResponse])
async def trigger_live_prediction(current_user: TokenData = Depends(get_current_user)):
    db = get_database()
    
    # 1. Fetch all locations and recent complaints to compute features
    locations = await db.locations.find({}, {"_id": 0}).to_list(length=100)
    complaints = await db.complaints.find({}, {"_id": 0}).to_list(length=100)
    
    if not locations:
         raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST,
             detail="No locations found in the database to evaluate."
         )
         
    # Prepare candidates list for ML API
    candidates = []
    now = datetime.now()
    hour_val = now.hour
    day_val = now.weekday()
    
    # Pre-calculate cyclical time features
    hour_sin = math.sin(2 * math.pi * hour_val / 24.0)
    hour_cos = math.cos(2 * math.pi * hour_val / 24.0)
    day_sin = math.sin(2 * math.pi * day_val / 7.0)
    day_cos = math.cos(2 * math.pi * day_val / 7.0)
    is_weekend = 1 if day_val >= 5 else 0
    
    for loc in locations:
        loc_id = loc.get("location_id", "")
        # Extract numeric id from location_id e.g. "ATM-104" -> 104
        numeric_id = 0
        try:
             numeric_id = int(''.join(filter(str.isdigit, loc_id)))
        except ValueError:
             numeric_id = 0
             
        geom = loc.get("geometry", {})
        coords = geom.get("coordinates", [0.0, 0.0]) # [longitude, latitude]
        lng, lat = coords[0], coords[1]
        
        # Aggregate complaints dynamically for this location / region
        loc_complaints = [c for c in complaints if c.get("region") == loc.get("region")]
        amounts = [float(c.get("amount", 0)) for c in loc_complaints if c.get("amount")]
        avg_amount = (sum(amounts) / len(amounts)) if amounts else 5000.0
        
        recent_txn = len(loc_complaints)
        recent_withdrawal = len([c for c in loc_complaints if "Skimming" in c.get("crime_category", "") or "Withdrawal" in c.get("crime_category", "")])
        
        # Construct Candidate Object structure matching ML model's LocationCandidate schema
        candidate = {
             "location_id": loc_id,
             "latitude": lat,
             "longitude": lng,
             "log_transaction_amount": math.log1p(avg_amount),
             "log_account_balance": math.log1p(avg_amount * 5.0),
             "recent_txn_count": recent_txn,
             "recent_withdrawal_count": recent_withdrawal,
             "withdrawal_ratio": recent_withdrawal / (recent_txn + 1.0),
             "distance_to_recent_withdrawal_km": 2.5 if recent_withdrawal > 0 else 0.5,
             "dist_from_last_txn_km": 1.2 if recent_txn > 0 else 0.0,
             "minutes_since_last_txn": 15.0 if recent_txn > 0 else 300.0,
             "withdrawals_past_1h": min(2, recent_withdrawal),
             "withdrawals_past_24h": recent_withdrawal,
             "location_density_30d": max(1, recent_withdrawal * 10),
             "historical_location_risk": loc.get("risk_score") or 0.35,
             "login_attempts": 2 if recent_withdrawal > 2 else 1,
             "transaction_duration": 45.0,
             "customer_age": 35,
             "hour_sin": hour_sin,
             "hour_cos": hour_cos,
             "day_sin": day_sin,
             "day_cos": day_cos,
             "is_weekend": is_weekend,
             "location_numeric_id": numeric_id,
             "crime_cat_routine_transaction": 0,
             "crime_cat_suspicious_cash_withdrawal": 1 if "Skimming" in loc.get("risk_level", "") or "CRITICAL" in loc.get("risk_level", "") else 0,
             "crime_cat_unusual_online_activity": 0,
             "crime_cat_high_value_transfer": 0
        }
        candidates.append(candidate)
        
    # 2. Call ML microservice
    ml_url = f"{settings.ml_service_url.rstrip('/')}/predict"
    payload = {
         "candidates": candidates,
         "predicted_window": "3h"
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
         try:
              response = await client.post(ml_url, json=payload)
              if response.status_code != 200:
                   raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"ML service returned error code {response.status_code}: {response.text}"
                   )
              ml_results = response.json()
         except httpx.RequestError as e:
              raise HTTPException(
                   status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                   detail=f"Unable to connect to ML service: {str(e)}"
              )
              
    # 3. Process results, update DB (upsert), and build response
    enriched_predictions = []
    
    for item in ml_results.get("predictions", []):
         loc_id = item.get("location_id")
         loc_doc = next((l for l in locations if l.get("location_id") == loc_id), {})
         
         prediction_doc = {
              "id": f"p_{loc_id.lower().replace('-', '_')}",
              "location_id": loc_id,
              "location_name": loc_doc.get("location_name", loc_id),
              "region": loc_doc.get("region", "Unknown"),
              "latitude": loc_doc.get("geometry", {}).get("coordinates", [0, 0])[1],
              "longitude": loc_doc.get("geometry", {}).get("coordinates", [0, 0])[0],
              "crime_category": loc_doc.get("crime_category", "Financial Cyber Fraud"),
              "risk_score": item.get("risk_score"),
              "risk_level": item.get("risk_level"),
              "predicted_window": item.get("predicted_window", "3h"),
              "rank": item.get("rank", 1),
              "top_factors": item.get("top_factors", []),
              "related_complaints": [c.get("complaint_id") for c in complaints if c.get("region") == loc_doc.get("region")][:3],
              "confidence": round(95.0 - item.get("rank", 1) * 2.0, 1),
              "case_id": None,
              "model_version": item.get("model_version", "iso_forest_v1_india"),
              "created_at": datetime.now(timezone.utc)
         }
         
         # Save to database (upsert based on location_id)
         await db.predictions.update_one(
              {"location_id": loc_id},
              {"$set": prediction_doc},
              upsert=True
         )
         
         # Retrieve the updated doc formatted to prediction response
         db_doc = await db.predictions.find_one({"location_id": loc_id}, {"_id": 0})
         enriched_predictions.append(PredictionResponse.model_validate(db_doc))
         
    return enriched_predictions