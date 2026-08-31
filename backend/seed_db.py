import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import certifi
import bcrypt

from app.config import settings

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

async def seed():
    print("Connecting to MongoDB Atlas...")
    try:
        client = AsyncIOMotorClient(
            settings.mongodb_connection_string,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000
        )
        await client.admin.command('ping')
    except Exception:
        client = AsyncIOMotorClient(
            settings.mongodb_connection_string,
            tlsCAFile=certifi.where(),
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=5000
        )
        await client.admin.command('ping')

    db = client[settings.mongodb_db_name]

    print("Cleaning existing collections...")
    await db.users.delete_many({})
    await db.locations.delete_many({})
    await db.predictions.delete_many({})
    await db.alerts.delete_many({})
    await db.cases.delete_many({})
    await db.complaints.delete_many({})

    print("Seeding Users with Bcrypt...")
    await db.users.insert_many([
        {
            "id": "u1",
            "username": "officer@cybersentinel.gov",
            "name": "Inspector Arjun Rao",
            "role": "LEA Officer",
            "password_hash": get_password_hash("officer123")
        },
        {
            "id": "u2",
            "username": "analyst@cybersentinel.gov",
            "name": "Nisha Verma",
            "role": "I4C Analyst",
            "password_hash": get_password_hash("analyst123")
        },
        {
            "id": "u3",
            "username": "bank@cybersentinel.gov",
            "name": "Kiran Shah",
            "role": "Bank/FI",
            "password_hash": get_password_hash("bank123")
        },
        {
            "id": "u4",
            "username": "admin@cybersentinel.gov",
            "name": "System Administrator",
            "role": "Admin",
            "password_hash": get_password_hash("admin123")
        },{
            "id": "u5",
            "username": "officer1@cybersentinel.gov",
            "name": "Inspector Pranjal Singh",
            "role": "LEA Officer",
            "password_hash": get_password_hash("officer123")
        }
    ])

    print("Seeding Complaints...")
    await db.complaints.insert_many([
        {
            "complaint_id": "C102",
            "timestamp": datetime.now(timezone.utc),
            "crime_category": "Financial Cyber Fraud",
            "region": "Vijayawada",
            "account_number": "ACC_XXXX_1042",
            "amount": 25000.0
        },
        {
            "complaint_id": "C183",
            "timestamp": datetime.now(timezone.utc),
            "crime_category": "ATM Skimming",
            "region": "Vijayawada",
            "account_number": "ACC_XXXX_8891",
            "amount": 10000.0
        },
        {
            "complaint_id": "C201",
            "timestamp": datetime.now(timezone.utc),
            "crime_category": "Financial Cyber Fraud",
            "region": "Vijayawada",
            "account_number": "ACC_XXXX_3201",
            "amount": 40000.0
        },
        {
            "complaint_id": "C244",
            "timestamp": datetime.now(timezone.utc),
            "crime_category": "ATM Skimming",
            "region": "Vijayawada",
            "account_number": "ACC_XXXX_4519",
            "amount": 15000.0
        },
        {
            "complaint_id": "C325",
            "timestamp": datetime.now(timezone.utc),
            "crime_category": "Financial Cyber Fraud",
            "region": "Hyderabad",
            "account_number": "ACC_XXXX_6023",
            "amount": 50000.0
        },
        {
            "complaint_id": "C388",
            "timestamp": datetime.now(timezone.utc),
            "crime_category": "Financial Cyber Fraud",
            "region": "Hyderabad",
            "account_number": "ACC_XXXX_7714",
            "amount": 35000.0
        },
        {
            "complaint_id": "C401",
            "timestamp": datetime.now(timezone.utc),
            "crime_category": "Account Takeover",
            "region": "Hyderabad",
            "account_number": "ACC_XXXX_9105",
            "amount": 75000.0
        },
        {
            "complaint_id": "C501",
            "timestamp": datetime.now(timezone.utc),
            "crime_category": "Phishing",
            "region": "Bengaluru",
            "account_number": "ACC_XXXX_5521",
            "amount": 18000.0
        }
    ])

    print("Seeding Cases...")
    await db.cases.insert_many([
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
    ])

    print("Seeding Locations...")
    await db.locations.insert_many([
        {
            "id": "loc_104",
            "location_id": "ATM-104",
            "location_name": "MG Road ATM Cluster",
            "region": "Vijayawada",
            "geometry": {"type": "Point", "coordinates": [80.6480, 16.5062]},
            "risk_score": 0.91,
            "risk_level": "CRITICAL",
            "predicted_window": "18:00–21:00",
            "location_metadata": {"atm_id": "ATM-104", "city": "Vijayawada", "type": "On-site Branch ATM"}
        },
        {
            "id": "loc_221",
            "location_id": "ATM-221",
            "location_name": "Benz Circle Banking Hub",
            "region": "Vijayawada",
            "geometry": {"type": "Point", "coordinates": [80.6558, 16.5044]},
            "risk_score": 0.86,
            "risk_level": "CRITICAL",
            "predicted_window": "20:00–23:00",
            "location_metadata": {"atm_id": "ATM-221", "city": "Vijayawada", "type": "Standalone Kiosk"}
        },
        {
            "id": "loc_087",
            "location_id": "ATM-087",
            "location_name": "KPHB Metro ATM",
            "region": "Hyderabad",
            "geometry": {"type": "Point", "coordinates": [78.3918, 17.4856]},
            "risk_score": 0.68,
            "risk_level": "HIGH",
            "predicted_window": "16:00–19:00",
            "location_metadata": {"atm_id": "ATM-087", "city": "Hyderabad", "type": "Transit ATM"}
        },
        {
            "id": "loc_176",
            "location_id": "ATM-176",
            "location_name": "Gachibowli Financial District",
            "region": "Hyderabad",
            "geometry": {"type": "Point", "coordinates": [78.3489, 17.4421]},
            "risk_score": 0.63,
            "risk_level": "HIGH",
            "predicted_window": "12:00–15:00",
            "location_metadata": {"atm_id": "ATM-176", "city": "Hyderabad", "type": "IT Park Kiosk"}
        },
        {
            "id": "loc_309",
            "location_id": "ATM-309",
            "location_name": "Indiranagar Service Point",
            "region": "Bengaluru",
            "geometry": {"type": "Point", "coordinates": [77.6408, 12.9784]},
            "risk_score": 0.54,
            "risk_level": "MEDIUM",
            "predicted_window": "09:00–12:00",
            "location_metadata": {"atm_id": "ATM-309", "city": "Bengaluru", "type": "Commercial Branch"}
        }
    ])

    print("Seeding Predictions...")
    await db.predictions.insert_many([
        {
            "id": "p104",
            "location_id": "ATM-104",
            "location_name": "MG Road ATM Cluster",
            "region": "Vijayawada",
            "latitude": 16.5062,
            "longitude": 80.6480,
            "risk_score": 0.91,
            "risk_level": "CRITICAL",
            "predicted_window": "18:00–21:00",
            "crime_category": "Financial Cyber Fraud",
            "rank": 1,
            "top_factors": [
                "Recent suspicious withdrawals nearby",
                "Similar historical transaction pattern",
                "High recent transaction activity",
                "Strong geographic correlation"
            ],
            "related_complaints": ["C102", "C183", "C201"],
            "model_version": "iso_forest_v1",
            "confidence": 94.0,
            "case_id": "CYB-2026-1024",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": "p221",
            "location_id": "ATM-221",
            "location_name": "Benz Circle Banking Hub",
            "region": "Vijayawada",
            "latitude": 16.5044,
            "longitude": 80.6558,
            "risk_score": 0.86,
            "risk_level": "CRITICAL",
            "predicted_window": "20:00–23:00",
            "crime_category": "ATM Skimming",
            "rank": 2,
            "top_factors": [
                "Device tampering indicators",
                "Repeat victim route overlap",
                "Night-time activity surge"
            ],
            "related_complaints": ["C183", "C244"],
            "model_version": "iso_forest_v1",
            "confidence": 89.0,
            "case_id": "CYB-2026-1024",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": "p087",
            "location_id": "ATM-087",
            "location_name": "KPHB Metro ATM",
            "region": "Hyderabad",
            "latitude": 17.4856,
            "longitude": 78.3918,
            "risk_score": 0.68,
            "risk_level": "HIGH",
            "predicted_window": "16:00–19:00",
            "crime_category": "Financial Cyber Fraud",
            "rank": 3,
            "top_factors": [
                "High-value transaction velocity",
                "Known mule account linkage",
                "Customer complaint density"
            ],
            "related_complaints": ["C325", "C388"],
            "model_version": "iso_forest_v1",
            "confidence": 82.0,
            "case_id": "CYB-2026-1029",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": "p176",
            "location_id": "ATM-176",
            "location_name": "Gachibowli Financial District",
            "region": "Hyderabad",
            "latitude": 17.4421,
            "longitude": 78.3489,
            "risk_score": 0.63,
            "risk_level": "HIGH",
            "predicted_window": "12:00–15:00",
            "crime_category": "Account Takeover",
            "rank": 4,
            "top_factors": [
                "Credential reuse signals",
                "Geo-velocity anomaly"
            ],
            "related_complaints": ["C401"],
            "model_version": "iso_forest_v1",
            "confidence": 78.0,
            "case_id": "CYB-2026-1029",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": "p309",
            "location_id": "ATM-309",
            "location_name": "Indiranagar Service Point",
            "region": "Bengaluru",
            "latitude": 12.9784,
            "longitude": 77.6408,
            "risk_score": 0.54,
            "risk_level": "MEDIUM",
            "predicted_window": "09:00–12:00",
            "crime_category": "Phishing",
            "rank": 5,
            "top_factors": [
                "Phishing report cluster",
                "Unusual cash-out pattern"
            ],
            "related_complaints": ["C501"],
            "model_version": "iso_forest_v1",
            "confidence": 71.0,
            "case_id": None,
            "created_at": datetime.now(timezone.utc)
        }
    ])

    print("Seeding Alerts...")
    await db.alerts.insert_many([
        {
            "id": "ALT-104",
            "prediction_id": "p104",
            "severity": "CRITICAL",
            "recipient_role": "LEA Officer",
            "status": "NEW",
            "created_at": datetime.now(timezone.utc),
            "acknowledged_at": None
        },
        {
            "id": "ALT-221",
            "prediction_id": "p221",
            "severity": "CRITICAL",
            "recipient_role": "LEA Officer",
            "status": "ACKNOWLEDGED",
            "created_at": datetime.now(timezone.utc),
            "acknowledged_at": datetime.now(timezone.utc)
        },
        {
            "id": "ALT-087",
            "prediction_id": "p087",
            "severity": "HIGH",
            "recipient_role": "LEA Officer",
            "status": "NEW",
            "created_at": datetime.now(timezone.utc),
            "acknowledged_at": None
        },
        {
            "id": "ALT-309",
            "prediction_id": "p309",
            "severity": "MEDIUM",
            "recipient_role": "LEA Officer",
            "status": "NEW",
            "created_at": datetime.now(timezone.utc),
            "acknowledged_at": None
        }
    ])

    print("MongoDB Atlas seeding completed successfully!")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
