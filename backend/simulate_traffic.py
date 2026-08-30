import math
import time
import random
import requests

# Backend API & ML Service Configuration
# Backend runs on port 8001, ML Microservice runs on port 8000
BACKEND_PORT = 8001
ML_PORT = 8000

PREDICT_URL = f"http://localhost:{BACKEND_PORT}/api/v1/predictions/predict-live"
DIRECT_ML_URL = f"http://localhost:{ML_PORT}/predict"
LOGIN_URL = f"http://localhost:{BACKEND_PORT}/api/v1/auth/login"

# Default LEA Officer credentials from backend seed (seed_db.py)
CREDENTIALS = {
    "email": "officer@cybersentinel.gov",
    "password": "officer123"
}

# Indian Cities & ATM location metadata matching ML dataset & MongoDB seeded locations
CITY_DATA = {
    "Vijayawada": {"lat": 16.5062, "lng": 80.6480, "loc_id": "ATM-104"},
    "Hyderabad": {"lat": 17.3850, "lng": 78.4867, "loc_id": "ATM-087"},
    "Bengaluru": {"lat": 12.9716, "lng": 77.5946, "loc_id": "ATM-309"},
    "Visakhapatnam": {"lat": 17.6868, "lng": 83.2185, "loc_id": "ATM-509"},
    "Chennai": {"lat": 13.0827, "lng": 80.2707, "loc_id": "ATM-401"},
    "Mumbai": {"lat": 19.0760, "lng": 72.8777, "loc_id": "ATM-602"},
    "Delhi": {"lat": 28.6139, "lng": 77.2090, "loc_id": "ATM-703"},
    "Guntur": {"lat": 16.3067, "lng": 80.4365, "loc_id": "ATM-804"},
    "Tirupati": {"lat": 13.6288, "lng": 79.4192, "loc_id": "ATM-905"},
}

CITIES = list(CITY_DATA.keys())

def get_auth_token():
    """Attempt to login to CyberSentinel Backend API and retrieve Bearer token."""
    try:
        res = requests.post(LOGIN_URL, json=CREDENTIALS, timeout=3)
        if res.status_code == 200:
            token = res.json().get("access_token")
            print("🔑 Successfully authenticated with CyberSentinel Backend API.")
            return token
    except Exception:
        pass
    return None

def build_ml_candidate(target_city: str, city_info: dict, is_attack: bool, amount: float, tx_freq: int, failed_attempts: int):
    """Build candidate vector matching ML Isolation Forest schema (predictionapi.py)."""
    hour = random.randint(0, 23)
    hour_sin = math.sin(2 * math.pi * hour / 24.0)
    hour_cos = math.cos(2 * math.pi * hour / 24.0)
    loc_num_id = int(''.join(filter(str.isdigit, city_info["loc_id"]))) if any(c.isdigit() for c in city_info["loc_id"]) else 100

    return {
        "location_id": city_info["loc_id"],
        "latitude": city_info["lat"],
        "longitude": city_info["lng"],
        "log_transaction_amount": float(math.log1p(amount)),
        "log_account_balance": float(math.log1p(50000 if is_attack else 25000)),
        "recent_txn_count": tx_freq,
        "recent_withdrawal_count": random.randint(10, 30) if is_attack else random.randint(0, 2),
        "withdrawal_ratio": 0.85 if is_attack else 0.1,
        "distance_to_recent_withdrawal_km": 250.0 if is_attack else 5.0,
        "dist_from_last_txn_km": 180.0 if is_attack else 2.0,
        "minutes_since_last_txn": 5.0 if is_attack else 30.0,
        "withdrawals_past_1h": tx_freq,
        "withdrawals_past_24h": tx_freq * 2,
        "location_density_30d": 150 if is_attack else 20,
        "historical_location_risk": 0.85 if is_attack else 0.35,
        "login_attempts": failed_attempts + 1,
        "transaction_duration": 15.0 if is_attack else 45.0,
        "customer_age": 35,
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
        "day_sin": 0.0,
        "day_cos": 1.0,
        "is_weekend": 0,
        "location_numeric_id": loc_num_id,
        "crime_cat_routine_transaction": 0 if is_attack else 1,
        "crime_cat_suspicious_cash_withdrawal": 1 if is_attack else 0,
        "crime_cat_unusual_online_activity": 0,
        "crime_cat_high_value_transfer": 1 if is_attack else 0
    }

def simulate_traffic():
    print("Starting live traffic simulation for CyberSentinel SIH demo...")
    print(f"Backend Endpoint: {PREDICT_URL}")
    print(f"Direct ML Endpoint: {DIRECT_ML_URL}")
    print(f"Monitoring Cities: {', '.join(CITIES)}\n")

    token = get_auth_token()

    while True:
        target_city = random.choice(CITIES)
        city_info = CITY_DATA[target_city]

        # 10% chance to simulate an "Attack" (Anomaly)
        is_attack = random.random() < 0.10

        if is_attack:
            tx_amount = random.randint(50000, 200000)
            tx_frequency = random.randint(50, 100)
            failed_attempts = random.randint(5, 15)
            print(f"🚨 ALERT: Injecting simulated attack at {target_city} ({city_info['loc_id']})! Amount: ₹{tx_amount}, Freq: {tx_frequency}, Failures: {failed_attempts}")
        else:
            tx_amount = random.randint(100, 5000)
            tx_frequency = random.randint(1, 5)
            failed_attempts = 0
            print(f"✅ Normal traffic logged at {target_city} ({city_info['loc_id']}). Amount: ₹{tx_amount}")

        # Payload matching Backend API live simulation request
        payload = {
            "location": target_city,
            "location_id": city_info["loc_id"],
            "latitude": city_info["lat"],
            "longitude": city_info["lng"],
            "tx_amount": tx_amount,
            "tx_frequency": tx_frequency,
            "failed_attempts": failed_attempts,
            "hour_of_day": random.randint(0, 23),
            "is_attack": is_attack
        }

        # Header with authorization token if available
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        sent_to_backend = False
        try:
            res = requests.post(PREDICT_URL, json=payload, headers=headers, timeout=5)
            if res.status_code in (200, 201):
                sent_to_backend = True
            elif res.status_code == 401 and not token:
                # Retry obtaining token if unauthenticated
                token = get_auth_token()
                if token:
                    headers = {"Authorization": f"Bearer {token}"}
                    res = requests.post(PREDICT_URL, json=payload, headers=headers, timeout=5)
                    sent_to_backend = (res.status_code in (200, 201))
        except requests.exceptions.RequestException:
            pass

        # If Backend live endpoint is offline or direct ML evaluation preferred, invoke ML microservice directly
        if not sent_to_backend:
            try:
                candidate = build_ml_candidate(target_city, city_info, is_attack, tx_amount, tx_frequency, failed_attempts)
                ml_payload = {"candidates": [candidate], "predicted_window": "3h"}
                ml_res = requests.post(DIRECT_ML_URL, json=ml_payload, timeout=5)
                if ml_res.status_code == 200:
                    scores = ml_res.json()
                    preds = scores.get("predictions", [])
                    if preds:
                        top_pred = preds[0]
                        print(f"   🤖 ML Model Evaluated -> Risk Score: {top_pred.get('risk_score')}, Level: {top_pred.get('risk_level')}")
            except requests.exceptions.RequestException as e:
                print(f"   ⚠️ Connection error: Backend ({PREDICT_URL}) and ML Service ({DIRECT_ML_URL}) unreachable.")

        # Wait 3 seconds before next transaction event
        time.sleep(3)

if __name__ == "__main__":
    simulate_traffic()
