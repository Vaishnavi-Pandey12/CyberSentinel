import os
from pymongo import MongoClient

try:
    import certifi
    cert_path = certifi.where()
except Exception:
    cert_path = None

try:
    from app.config import settings
    default_uri = settings.mongodb_connection_string or "mongodb://localhost:27017/"
    default_db = settings.mongodb_db_name or "cybersentinel"
except Exception:
    default_uri = "mongodb://localhost:27017/"
    default_db = "cybersentinel"

MONGO_URI = os.getenv("MONGO_URI", default_uri)
DB_NAME = os.getenv("MONGO_DB_NAME", default_db)

try:
    if cert_path:
        client = MongoClient(MONGO_URI, tlsCAFile=cert_path, serverSelectionTimeoutMS=5000)
    else:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
except Exception:
    try:
        if cert_path:
            client = MongoClient(MONGO_URI, tlsCAFile=cert_path, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=5000)
        else:
            client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
    except Exception:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

db_names = ["cybersentinel", "cybersentinel_db"]

def seed_database():
    for db_name in db_names:
        db = client[db_name]
        nodes_col = db["nodes"]
        edges_col = db["edges"]
        audit_col = db["audit_logs"]

        print(f"[INIT] Wiping existing database '{db_name}' to prevent floating nodes...")
        nodes_col.delete_many({})
        edges_col.delete_many({})
        audit_col.delete_many({})

        print(f"[SEED] Seeding Victim Node in '{db_name}'...")
        victim_id = nodes_col.insert_one({
            "type": "VICTIM",
            "riskScore": 95, 
            "status": "ACTIVE",
            "metadata": {"label": "Victim Account (HDFC)"}
        }).inserted_id

        print(f"[SEED] Seeding Mule Nodes in '{db_name}'...")
        mule1_id = nodes_col.insert_one({
            "type": "MULE",
            "riskScore": 75,
            "status": "ACTIVE",
            "metadata": {"label": "Mule Account 101 (SBI)"}
        }).inserted_id

        mule2_id = nodes_col.insert_one({
            "type": "MULE",
            "riskScore": 60,
            "status": "ACTIVE",
            "metadata": {"label": "Mule Account 202 (ICICI)"}
        }).inserted_id

        mule3_id = nodes_col.insert_one({
            "type": "MULE",
            "riskScore": 85,
            "status": "ACTIVE",
            "metadata": {"label": "Mule Account 303 (Axis)"}
        }).inserted_id

        print(f"[SEED] Seeding Shared IP/Device Node in '{db_name}'...")
        device_id = nodes_col.insert_one({
            "type": "DEVICE",
            "riskScore": 90,
            "status": "ACTIVE",
            "metadata": {"label": "Shared IP (192.168.x.x)", "ip": "192.168.1.45"}
        }).inserted_id

        print(f"[SEED] Seeding ATM Nodes (Pan-India Scale) in '{db_name}'...")
        atms = [
            {"label": "ATM - Connaught Place, New Delhi", "lat": 28.6304, "lng": 77.2177},
            {"label": "ATM - Bandra Kurla Complex, Mumbai", "lat": 19.0650, "lng": 72.8653},
            {"label": "ATM - Koramangala, Bengaluru", "lat": 12.9279, "lng": 77.6271},
            {"label": "ATM - Salt Lake Sector V, Kolkata", "lat": 22.5735, "lng": 88.4334},
            {"label": "ATM - HITEC City, Hyderabad", "lat": 17.4435, "lng": 78.3772},
            {"label": "ATM - Benz Circle, Vijayawada", "lat": 16.4971, "lng": 80.6516}
        ]
        
        atm_ids = []
        for atm in atms:
            atm_ids.append(nodes_col.insert_one({
                "type": "ATM",
                "riskScore": 0, 
                "status": "ACTIVE",
                "metadata": atm
            }).inserted_id)

        print(f"[LINK] Linking the Money Trail (Edges) in '{db_name}'...")
        
        edges_col.insert_many([
            {"source": victim_id, "target": mule1_id, "type": "TRANSFER", "weight": 50000},
            {"source": victim_id, "target": mule2_id, "type": "TRANSFER", "weight": 75000}
        ])

        edges_col.insert_many([
            {"source": mule1_id, "target": device_id, "type": "SHARED_KYC"},
            {"source": mule2_id, "target": device_id, "type": "SHARED_KYC"},
            {"source": mule3_id, "target": device_id, "type": "SHARED_KYC"}
        ])

        edges_col.insert_one(
            {"source": mule1_id, "target": mule3_id, "type": "TRANSFER", "weight": 48000}
        )

        # Link the mules to these spread-out ATMs across Pan-India banking corridors
        edges_col.insert_many([
            {"source": mule2_id, "target": atm_ids[0], "type": "CASH_WITHDRAWAL"}, # Delhi
            {"source": mule2_id, "target": atm_ids[1], "type": "CASH_WITHDRAWAL"}, # Mumbai
            {"source": mule3_id, "target": atm_ids[2], "type": "CASH_WITHDRAWAL"}, # Bengaluru
            {"source": mule3_id, "target": atm_ids[3], "type": "CASH_WITHDRAWAL"}, # Kolkata
            {"source": mule1_id, "target": atm_ids[4], "type": "CASH_WITHDRAWAL"}, # Hyderabad
            {"source": mule1_id, "target": atm_ids[5], "type": "CASH_WITHDRAWAL"}  # Vijayawada
        ])

        print(f"[SUCCESS] Database '{db_name}' Seeded Successfully with Pan-India Nodes!")

if __name__ == "__main__":
    seed_database()
