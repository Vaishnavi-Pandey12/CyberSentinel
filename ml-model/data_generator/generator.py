"""
CyberSentinel Synthetic Data Generator
Generates realistic complaints, transactions, ATMs, accounts, and unified ML dataset
grounded in public research data from NCERT 2024 ATM Hotspots, NCRP State Cybercrime data,
and Delhi Police ATM security survey statistics.
"""
import os
import hmac
import hashlib
import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd

from data_generator.public_data_loader import PublicDataDistributions
from data_generator.distributions import (
    INDIAN_BANKS, BANK_WEIGHTS,
    CHANNELS, CHANNEL_WEIGHTS_NORMAL, CHANNEL_WEIGHTS_FRAUD,
    LOCATION_TYPES, LOCATION_TYPE_WEIGHTS,
    FRAUD_CATEGORIES, FRAUD_CATEGORY_WEIGHTS,
    ID_TYPES, GENDERS, GENDER_WEIGHTS,
    COMPLAINT_CHANNELS,
    sample_normal_amount, sample_fraud_amount
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTHETIC_DIR = os.path.join(BASE_DIR, "data", "synthetic")
SECRET_KEY = os.getenv("CYBERSENTINEL_HMAC_SECRET", "cybersentinel_secure_salt_2026").encode("utf-8")

def hash_account_id(raw_acc_id: str) -> str:
    """Pseudonymize account identifier with HMAC-SHA256."""
    return hmac.new(SECRET_KEY, raw_acc_id.encode("utf-8"), hashlib.sha256).hexdigest()[:16]

def normalize_p(probs: List[float]) -> np.ndarray:
    arr = np.array(probs, dtype=float)
    return arr / arr.sum()

class SyntheticDataEngine:
    def __init__(self, seed: int = 20260923):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.priors = PublicDataDistributions()
        os.makedirs(SYNTHETIC_DIR, exist_ok=True)

    def generate_atms(self, num_atms: int = 600) -> pd.DataFrame:
        print(f"[1/5] Generating {num_atms} synthetic ATMs grounded in NCERT hotspot distribution...")
        atms = []
        bank_p = normalize_p(BANK_WEIGHTS)
        loc_p = normalize_p(LOCATION_TYPE_WEIGHTS)

        for i in range(num_atms):
            city_info = self.priors.sample_hotspot_city(self.rng)
            city = city_info["city"]
            state = city_info["state"]
            district = city_info["district"]
            base_lat = city_info["latitude"]
            base_lon = city_info["longitude"]

            lat = round(base_lat + float(self.rng.normal(0, 0.035)), 6)
            lon = round(base_lon + float(self.rng.normal(0, 0.035)), 6)

            bank = str(self.rng.choice(INDIAN_BANKS, p=bank_p))
            loc_type = str(self.rng.choice(LOCATION_TYPES, p=loc_p))
            is_onsite = bool(self.rng.random() > 0.55)
            is_indoor = bool(self.rng.random() > 0.40)
            atm_type = str(self.rng.choice(["Bank-Owned", "White-Label", "Brown-Label"], p=normalize_p([0.60, 0.25, 0.15])))
            
            if city == "Delhi":
                guard_present = bool(self.rng.random() > self.priors.guard_missing_rate)
                lock_present = bool(self.rng.random() > self.priors.lock_missing_rate)
            else:
                guard_present = bool(self.rng.random() > 0.40)
                lock_present = bool(self.rng.random() > 0.35)

            cctv_available = bool(self.rng.random() > 0.15)
            cctv_footage = bool(cctv_available and self.rng.random() > 0.30)
            
            atm_code = city[:3].upper()
            atm_id = f"ATM_{atm_code}_{i+1:04d}"
            clean_loc = loc_type.replace("_", " ")

            atms.append({
                "ATM_ID": atm_id,
                "ATM_Bank": bank,
                "ATM_Location": f"{clean_loc} Kiosk, {city}",
                "ATM_City": city,
                "ATM_District": district,
                "ATM_State": state,
                "ATM_Latitude": lat,
                "ATM_Longitude": lon,
                "ATM_Type": atm_type,
                "ATM_Onsite_Offsite": "Onsite" if is_onsite else "Offsite",
                "ATM_Indoor_Outdoor": "Indoor" if is_indoor else "Outdoor",
                "ATM_Operating_Status": "Active" if self.rng.random() > 0.05 else "Degraded",
                "CCTV_Available": cctv_available,
                "CCTV_Footage_Available": cctv_footage,
                "CCTV_Footage_Reviewed": bool(cctv_footage and self.rng.random() > 0.50),
                "Card_Skimming_Device_Detected": False,
                "ATM_Tampering_Detected": False,
                "ATM_Malfunction": bool(self.rng.random() < 0.03),
                "Security_Guard_Present": guard_present,
                "Shutter_Lock_Present": lock_present,
                "Location_Type": loc_type,
                "Urban_Rural": "Urban" if loc_type in ["Commercial_Area", "Shopping_Mall", "Airport"] else "Semi-Urban"
            })

        df_atms = pd.DataFrame(atms)
        df_atms.to_csv(os.path.join(SYNTHETIC_DIR, "synthetic_atms.csv"), index=False)
        print(f"  [OK] Saved {len(df_atms)} ATMs to synthetic_atms.csv")
        return df_atms

    def generate_accounts(self, num_accounts: int = 15000) -> pd.DataFrame:
        print(f"[2/5] Generating {num_accounts} synthetic accounts with HMAC-SHA256 pseudonymization...")
        accounts = []
        bank_p = normalize_p(BANK_WEIGHTS)
        role_p = normalize_p([0.88, 0.05, 0.04, 0.02, 0.01])

        for i in range(num_accounts):
            raw_id = f"ACCT_{i+1:08d}"
            hashed_id = hash_account_id(raw_id)
            role = str(self.rng.choice(
                ["Normal", "Victim", "Mule_L1", "Mule_L2", "Mule_L3"],
                p=role_p
            ))
            bank = str(self.rng.choice(INDIAN_BANKS, p=bank_p))
            city_info = self.priors.sample_hotspot_city(self.rng)
            balance = float(round(float(self.rng.lognormal(mean=9.5, sigma=1.2)), 2))
            balance = float(np.clip(balance, 500.0, 5000000.0))

            accounts.append({
                "account_internal_id": raw_id,
                "hashedAccNo": hashed_id,
                "account_type": role,
                "bank_name": bank,
                "home_city": city_info["city"],
                "home_state": city_info["state"],
                "account_balance": balance
            })

        df_accounts = pd.DataFrame(accounts)
        df_accounts.to_csv(os.path.join(SYNTHETIC_DIR, "synthetic_accounts.csv"), index=False)
        print(f"  [OK] Saved {len(df_accounts)} accounts to synthetic_accounts.csv")
        return df_accounts

    def generate_transactions_and_complaints(
        self,
        df_atms: pd.DataFrame,
        df_accounts: pd.DataFrame,
        num_transactions: int = 60000,
        start_date: str = "2026-06-01",
        end_date: str = "2026-09-20"
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        print(f"[3/5] Simulating {num_transactions} transactions over timeline ({start_date} to {end_date})...")

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        total_seconds = int((end_dt - start_dt).total_seconds())

        normal_accounts = df_accounts[df_accounts["account_type"] == "Normal"]["hashedAccNo"].values
        victim_accounts = df_accounts[df_accounts["account_type"] == "Victim"]["hashedAccNo"].values
        mule_l1 = df_accounts[df_accounts["account_type"] == "Mule_L1"]["hashedAccNo"].values
        mule_l2 = df_accounts[df_accounts["account_type"] == "Mule_L2"]["hashedAccNo"].values
        mule_l3 = df_accounts[df_accounts["account_type"] == "Mule_L3"]["hashedAccNo"].values

        atms_records = df_atms.to_dict(orient="records")
        atm_by_city = {}
        for a in atms_records:
            atm_by_city.setdefault(a["ATM_City"], []).append(a)

        transactions = []
        complaints = []
        tx_count = 0
        cmp_count = 0

        channel_normal_p = normalize_p(CHANNEL_WEIGHTS_NORMAL)
        bank_p = normalize_p(BANK_WEIGHTS)
        fraud_cat_p = normalize_p(FRAUD_CATEGORY_WEIGHTS)
        gender_p = normalize_p(GENDER_WEIGHTS)

        num_normal = int(num_transactions * 0.82)
        print(f"  Generating {num_normal} normal transactions...")
        for _ in range(num_normal):
            tx_count += 1
            sec_offset = int(self.rng.integers(0, total_seconds))
            current_dt = start_dt + timedelta(seconds=sec_offset)
            hour_probs = normalize_p([0.01, 0.01, 0.01, 0.01, 0.01, 0.02, 0.03, 0.05, 0.06, 0.07, 0.08, 0.08, 0.08, 0.07, 0.06, 0.06, 0.07, 0.08, 0.07, 0.05, 0.04, 0.02, 0.01, 0.01])
            hour = int(self.rng.choice(24, p=hour_probs))
            current_dt = current_dt.replace(hour=hour, minute=int(self.rng.integers(0, 60)), second=int(self.rng.integers(0, 60)))

            channel = str(self.rng.choice(CHANNELS, p=channel_normal_p))
            amount = sample_normal_amount(self.rng, channel)
            src_acc = str(self.rng.choice(normal_accounts))
            dst_acc = str(self.rng.choice(normal_accounts))
            bank = str(self.rng.choice(INDIAN_BANKS, p=bank_p))

            if channel == "ATM":
                city_info = self.priors.sample_hotspot_city(self.rng)
                city_atms = atm_by_city.get(city_info["city"], atms_records)
                atm_obj = self.rng.choice(city_atms)
                city = atm_obj["ATM_City"]
                district = atm_obj["ATM_District"]
                state = atm_obj["ATM_State"]
                lat = atm_obj["ATM_Latitude"]
                lon = atm_obj["ATM_Longitude"]
                atm_id = atm_obj["ATM_ID"]
            else:
                city_info = self.priors.sample_hotspot_city(self.rng)
                city = city_info["city"]
                district = city_info["district"]
                state = city_info["state"]
                lat = city_info["latitude"] + float(self.rng.normal(0, 0.02))
                lon = city_info["longitude"] + float(self.rng.normal(0, 0.02))
                atm_id = "NONE"

            tx_id = f"TXN_{current_dt.strftime('%Y%m%d')}_{tx_count:06d}"
            tx_type = "Debit" if channel == "ATM" else str(self.rng.choice(["Transfer", "Debit", "Credit"], p=normalize_p([0.5, 0.3, 0.2])))
            utr_ref = f"UTR{current_dt.strftime('%Y%m%d')}{self.rng.integers(100000, 999999)}"

            transactions.append({
                "Transaction_ID": tx_id,
                "Transaction_Reference": utr_ref,
                "Transaction_Date": current_dt.strftime("%Y-%m-%d"),
                "Transaction_Time": current_dt.strftime("%H:%M:%S"),
                "prediction_timestamp": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "Transaction_Amount": amount,
                "Transaction_Type": tx_type,
                "Payment_Mode": channel,
                "Channel": channel,
                "Bank_Name": bank,
                "sourceHashedAccNo": src_acc,
                "destinationHashedAccNo": dst_acc,
                "ATM_ID": atm_id,
                "City": city,
                "District": district,
                "State": state,
                "Latitude": round(lat, 6),
                "Longitude": round(lon, 6),
                "Is_Fraud": 0,
                "Fraud_Type": "None",
                "Mule_Chain_Hop": 0,
                "DeviceID": f"DEV_{self.rng.integers(1000, 9999)}",
                "IP_Address": f"103.{self.rng.integers(10, 250)}.{self.rng.integers(1, 250)}.{self.rng.integers(1, 250)}",
                "LoginAttempts": 1 if self.rng.random() > 0.03 else 2,
                "TransactionDuration": round(float(self.rng.exponential(scale=30) + 10), 1),
                "AccountBalance": round(float(self.rng.lognormal(mean=9.0, sigma=1.0)), 2)
            })

        # Step B: Fraudulent Multi-Hop Mule Chains and ATM Cash-Outs (~18%)
        num_fraud_chains = int((num_transactions - num_normal) / 3.5)
        print(f"  Generating {num_fraud_chains} multi-hop fraud chains terminating at hotspot ATMs...")

        for _ in range(num_fraud_chains):
            chain_sec = int(self.rng.integers(0, total_seconds))
            chain_dt = start_dt + timedelta(seconds=chain_sec)
            
            is_night_cashout = bool(self.rng.random() > 0.45)
            hour = int(self.rng.choice([22, 23, 0, 1, 2, 3, 4, 5]) if is_night_cashout else self.rng.integers(10, 20))
            chain_dt = chain_dt.replace(hour=hour, minute=int(self.rng.integers(0, 60)), second=int(self.rng.integers(0, 60)))

            victim_acc = str(self.rng.choice(victim_accounts))
            m1 = str(self.rng.choice(mule_l1))
            m2 = str(self.rng.choice(mule_l2))
            fraud_cat = str(self.rng.choice(FRAUD_CATEGORIES, p=fraud_cat_p))
            initial_fraud_amt = sample_fraud_amount(self.rng, "UPI")

            city_info = self.priors.sample_hotspot_city(self.rng)
            city_atms = atm_by_city.get(city_info["city"], atms_records)
            cashout_atm = self.rng.choice(city_atms)

            # Hop 1: Victim -> Mule 1
            tx_count += 1
            t1_time = chain_dt
            tx1_id = f"TXN_{t1_time.strftime('%Y%m%d')}_{tx_count:06d}"
            transactions.append({
                "Transaction_ID": tx1_id,
                "Transaction_Reference": f"UTR{t1_time.strftime('%Y%m%d')}{self.rng.integers(100000, 999999)}",
                "Transaction_Date": t1_time.strftime("%Y-%m-%d"),
                "Transaction_Time": t1_time.strftime("%H:%M:%S"),
                "prediction_timestamp": t1_time.strftime("%Y-%m-%d %H:%M:%S"),
                "Transaction_Amount": initial_fraud_amt,
                "Transaction_Type": "Transfer",
                "Payment_Mode": "UPI",
                "Channel": "UPI",
                "Bank_Name": cashout_atm["ATM_Bank"],
                "sourceHashedAccNo": victim_acc,
                "destinationHashedAccNo": m1,
                "ATM_ID": "NONE",
                "City": city_info["city"],
                "District": city_info["district"],
                "State": city_info["state"],
                "Latitude": round(city_info["latitude"] + float(self.rng.normal(0, 0.01)), 6),
                "Longitude": round(city_info["longitude"] + float(self.rng.normal(0, 0.01)), 6),
                "Is_Fraud": 1,
                "Fraud_Type": fraud_cat,
                "Mule_Chain_Hop": 1,
                "DeviceID": f"DEV_MULE_{self.rng.integers(100, 999)}",
                "IP_Address": f"182.{self.rng.integers(10, 250)}.{self.rng.integers(1, 250)}.{self.rng.integers(1, 250)}",
                "LoginAttempts": 3,
                "TransactionDuration": round(float(self.rng.exponential(scale=15) + 5), 1),
                "AccountBalance": round(float(self.rng.lognormal(mean=8.5, sigma=1.0)), 2)
            })

            # Hop 2: Mule 1 -> Mule 2
            tx_count += 1
            t2_time = t1_time + timedelta(minutes=int(self.rng.integers(3, 20)))
            tx2_id = f"TXN_{t2_time.strftime('%Y%m%d')}_{tx_count:06d}"
            split_amt = round(initial_fraud_amt * float(self.rng.uniform(0.70, 0.95)), 2)
            transactions.append({
                "Transaction_ID": tx2_id,
                "Transaction_Reference": f"UTR{t2_time.strftime('%Y%m%d')}{self.rng.integers(100000, 999999)}",
                "Transaction_Date": t2_time.strftime("%Y-%m-%d"),
                "Transaction_Time": t2_time.strftime("%H:%M:%S"),
                "prediction_timestamp": t2_time.strftime("%Y-%m-%d %H:%M:%S"),
                "Transaction_Amount": split_amt,
                "Transaction_Type": "Transfer",
                "Payment_Mode": "UPI",
                "Channel": "UPI",
                "Bank_Name": cashout_atm["ATM_Bank"],
                "sourceHashedAccNo": m1,
                "destinationHashedAccNo": m2,
                "ATM_ID": "NONE",
                "City": city_info["city"],
                "District": city_info["district"],
                "State": city_info["state"],
                "Latitude": round(city_info["latitude"] + float(self.rng.normal(0, 0.01)), 6),
                "Longitude": round(city_info["longitude"] + float(self.rng.normal(0, 0.01)), 6),
                "Is_Fraud": 1,
                "Fraud_Type": fraud_cat,
                "Mule_Chain_Hop": 2,
                "DeviceID": f"DEV_MULE_{self.rng.integers(100, 999)}",
                "IP_Address": f"182.{self.rng.integers(10, 250)}.{self.rng.integers(1, 250)}.{self.rng.integers(1, 250)}",
                "LoginAttempts": 2,
                "TransactionDuration": round(float(self.rng.exponential(scale=20) + 5), 1),
                "AccountBalance": round(float(self.rng.lognormal(mean=8.0, sigma=1.0)), 2)
            })

            # Hop 3: Terminal Fraudulent ATM Cash-Out at Hotspot ATM
            tx_count += 1
            t3_time = t2_time + timedelta(minutes=int(self.rng.integers(5, 45)))
            tx3_id = f"TXN_{t3_time.strftime('%Y%m%d')}_{tx_count:06d}"
            cashout_amt = sample_fraud_amount(self.rng, "ATM", is_cashout=True)
            transactions.append({
                "Transaction_ID": tx3_id,
                "Transaction_Reference": f"UTR{t3_time.strftime('%Y%m%d')}{self.rng.integers(100000, 999999)}",
                "Transaction_Date": t3_time.strftime("%Y-%m-%d"),
                "Transaction_Time": t3_time.strftime("%H:%M:%S"),
                "prediction_timestamp": t3_time.strftime("%Y-%m-%d %H:%M:%S"),
                "Transaction_Amount": cashout_amt,
                "Transaction_Type": "Debit",
                "Payment_Mode": "ATM",
                "Channel": "ATM",
                "Bank_Name": cashout_atm["ATM_Bank"],
                "sourceHashedAccNo": m2,
                "destinationHashedAccNo": hash_account_id("ATM_CASHOUT_TERMINAL"),
                "ATM_ID": cashout_atm["ATM_ID"],
                "City": cashout_atm["ATM_City"],
                "District": cashout_atm["ATM_District"],
                "State": cashout_atm["ATM_State"],
                "Latitude": cashout_atm["ATM_Latitude"],
                "Longitude": cashout_atm["ATM_Longitude"],
                "Is_Fraud": 1,
                "Fraud_Type": "Unauthorized ATM Cash-Out",
                "Mule_Chain_Hop": 3,
                "DeviceID": f"DEV_ATM_{cashout_atm['ATM_ID'][-4:]}",
                "IP_Address": f"10.24.{self.rng.integers(1, 250)}.{self.rng.integers(1, 250)}",
                "LoginAttempts": int(self.rng.choice([1, 2, 3], p=normalize_p([0.4, 0.4, 0.2]))),
                "TransactionDuration": round(float(self.rng.exponential(scale=45) + 20), 1),
                "AccountBalance": round(float(self.rng.lognormal(mean=7.0, sigma=1.0)), 2)
            })

            # Corresponding Victim Complaint
            cmp_count += 1
            cmp_time = t1_time + timedelta(hours=int(self.rng.integers(1, 48)))
            complaints.append({
                "Complaint_ID": f"CMP_{cmp_time.strftime('%Y%m%d')}_{cmp_count:05d}",
                "Complaint_Date": cmp_time.strftime("%Y-%m-%d"),
                "Complaint_Time": cmp_time.strftime("%H:%M:%S"),
                "Complaint_Channel": str(self.rng.choice(COMPLAINT_CHANNELS)),
                "Complainant_Age": int(self.rng.integers(21, 72)),
                "Complainant_Gender": str(self.rng.choice(GENDERS, p=gender_p)),
                "Complainant_State": city_info["state"],
                "Complainant_District": city_info["district"],
                "Complainant_City": city_info["city"],
                "Complainant_Pincode": f"{self.rng.integers(110001, 850000)}",
                "Complainant_ID_Type": str(self.rng.choice(ID_TYPES)),
                "Incident_Date": t1_time.strftime("%Y-%m-%d"),
                "Incident_Time": t1_time.strftime("%H:%M:%S"),
                "Incident_Type": "Financial Cyber-Fraud",
                "Fraud_Type": fraud_cat,
                "Incident_Description": f"Victim reported unauthorized transfer followed by ATM cashout ring in {city_info['city']}",
                "Incident_State": city_info["state"],
                "Incident_District": city_info["district"],
                "Incident_City": city_info["city"],
                "Incident_Location": f"{city_info['city']} Commercial Sector",
                "Transaction_ID": tx1_id,
                "Transaction_Amount": initial_fraud_amt,
                "Payment_Mode": "UPI",
                "Bank_Name": cashout_atm["ATM_Bank"],
                "ATM_ID": cashout_atm["ATM_ID"],
                "ATM_Location": cashout_atm["ATM_Location"],
                "Evidence_Available": 1,
                "Bank_Statement_Available": 1,
                "Transaction_Receipt_Available": 1 if self.rng.random() > 0.3 else 0,
                "Screenshot_Available": 1 if self.rng.random() > 0.2 else 0
            })

        df_tx = pd.DataFrame(transactions)
        df_cmp = pd.DataFrame(complaints)

        # Sort Chronologically
        df_tx["prediction_timestamp"] = pd.to_datetime(df_tx["prediction_timestamp"])
        df_tx = df_tx.sort_values("prediction_timestamp").reset_index(drop=True)
        df_tx["prediction_timestamp"] = df_tx["prediction_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

        df_cmp["Complaint_Timestamp"] = pd.to_datetime(df_cmp["Complaint_Date"] + " " + df_cmp["Complaint_Time"])
        df_cmp = df_cmp.sort_values("Complaint_Timestamp").drop(columns=["Complaint_Timestamp"]).reset_index(drop=True)

        # Save Raw Tables
        df_tx.to_csv(os.path.join(SYNTHETIC_DIR, "synthetic_transactions.csv"), index=False)
        df_cmp.to_csv(os.path.join(SYNTHETIC_DIR, "synthetic_complaints.csv"), index=False)
        print(f"  [OK] Saved {len(df_tx):,} transactions to synthetic_transactions.csv")
        print(f"  [OK] Saved {len(df_cmp):,} complaints to synthetic_complaints.csv")

        # Generate Unified Historical ML Dataset
        print("[4/5] Building unified historical ML dataset...")
        df_unified = df_tx.merge(
            df_atms[["ATM_ID", "ATM_Type", "ATM_Onsite_Offsite", "ATM_Indoor_Outdoor", "ATM_Operating_Status", "CCTV_Available", "Security_Guard_Present", "Shutter_Lock_Present", "Location_Type", "Urban_Rural"]],
            on="ATM_ID",
            how="left"
        )
        df_unified["ATM_Type"] = df_unified["ATM_Type"].fillna("Online/Digital")
        df_unified["ATM_Onsite_Offsite"] = df_unified["ATM_Onsite_Offsite"].fillna("None")
        df_unified["ATM_Indoor_Outdoor"] = df_unified["ATM_Indoor_Outdoor"].fillna("None")
        df_unified["ATM_Operating_Status"] = df_unified["ATM_Operating_Status"].fillna("Active")
        df_unified["CCTV_Available"] = df_unified["CCTV_Available"].fillna(False)
        df_unified["Security_Guard_Present"] = df_unified["Security_Guard_Present"].fillna(False)
        df_unified["Shutter_Lock_Present"] = df_unified["Shutter_Lock_Present"].fillna(False)
        df_unified["Location_Type"] = df_unified["Location_Type"].fillna("Commercial_Area")
        df_unified["Urban_Rural"] = df_unified["Urban_Rural"].fillna("Urban")

        df_unified.to_csv(os.path.join(SYNTHETIC_DIR, "synthetic_historical_ml_dataset.csv"), index=False)
        print(f"  [OK] Saved {len(df_unified):,} unified rows to synthetic_historical_ml_dataset.csv")

        # Provenance Metadata
        metadata = {
            "dataset_name": "cybersentinel_synthetic_v1",
            "generated_at": datetime.now().isoformat(),
            "random_seed": self.seed,
            "public_sources": [
                "2024 NCERT cybercrime trends presentation - ATM Hotspots intelligence table",
                "NCRP State-level cyber-fraud reported incident statistics",
                "Historical ATM physical crime hotspots 2018-19",
                "Delhi Police ATM security survey 2024 (2,000+ unguarded ATMs, 2,765 unlocked shutters)"
            ],
            "total_atms": len(df_atms),
            "total_accounts": len(df_accounts),
            "total_transactions": len(df_tx),
            "total_complaints": len(df_cmp),
            "fraud_transaction_rate": round(float(df_tx["Is_Fraud"].mean()), 4),
            "city_transaction_distribution": df_tx["City"].value_counts().to_dict()
        }
        with open(os.path.join(SYNTHETIC_DIR, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        print("[5/5] Saved dataset metadata to data/synthetic/metadata.json")

        return df_atms, df_tx, df_cmp

def main():
    parser = argparse.ArgumentParser(description="Generate CyberSentinel Synthetic Dataset from PDF Priors")
    parser.add_argument("--num-atms", type=int, default=600, help="Number of ATMs to generate")
    parser.add_argument("--num-accounts", type=int, default=15000, help="Number of accounts to generate")
    parser.add_argument("--num-transactions", type=int, default=60000, help="Number of transactions to simulate")
    parser.add_argument("--seed", type=int, default=20260923, help="Random seed for reproducibility")
    args = parser.parse_args()

    engine = SyntheticDataEngine(seed=args.seed)
    df_atms = engine.generate_atms(num_atms=args.num_atms)
    df_accounts = engine.generate_accounts(num_accounts=args.num_accounts)
    engine.generate_transactions_and_complaints(
        df_atms=df_atms,
        df_accounts=df_accounts,
        num_transactions=args.num_transactions
    )
    print("\n======================================================")
    print("  SYNTHETIC DATASET GENERATION SUCCESSFULLY COMPLETED  ")
    print("======================================================")

if __name__ == "__main__":
    main()
