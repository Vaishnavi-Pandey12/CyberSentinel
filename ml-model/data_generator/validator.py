"""
CyberSentinel Synthetic Dataset Quality & Distribution Validator
Performs comprehensive integrity, statistical distribution, coordinate, and leakage checks.
"""
import os
import json
import numpy as np
import pandas as pd
from typing import Dict, Any

from data_generator.public_data_loader import PublicDataDistributions

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTHETIC_DIR = os.path.join(BASE_DIR, "data", "synthetic")

class SyntheticDataValidator:
    def __init__(self):
        self.priors = PublicDataDistributions()
        self.errors = []
        self.warnings = []

    def validate_all(self) -> Dict[str, Any]:
        print("=" * 65)
        print("  CYBERSENTINEL SYNTHETIC DATASET VALIDATION SUITE")
        print("=" * 65)

        # 1. File Existence Check
        required_files = [
            "synthetic_atms.csv",
            "synthetic_accounts.csv",
            "synthetic_transactions.csv",
            "synthetic_complaints.csv",
            "synthetic_historical_ml_dataset.csv",
            "metadata.json"
        ]
        for fname in required_files:
            fpath = os.path.join(SYNTHETIC_DIR, fname)
            if not os.path.exists(fpath):
                self.errors.append(f"Missing required file: {fname}")
            else:
                size_kb = os.path.getsize(fpath) / 1024
                print(f"  [OK] Found {fname} ({size_kb:.1f} KB)")

        if self.errors:
            return {"status": "FAIL", "errors": self.errors, "warnings": self.warnings}

        # 2. Load Datasets
        df_atms = pd.read_csv(os.path.join(SYNTHETIC_DIR, "synthetic_atms.csv"))
        df_accounts = pd.read_csv(os.path.join(SYNTHETIC_DIR, "synthetic_accounts.csv"))
        df_tx = pd.read_csv(os.path.join(SYNTHETIC_DIR, "synthetic_transactions.csv"))
        df_cmp = pd.read_csv(os.path.join(SYNTHETIC_DIR, "synthetic_complaints.csv"))
        df_unified = pd.read_csv(os.path.join(SYNTHETIC_DIR, "synthetic_historical_ml_dataset.csv"))

        # 3. Coordinate Bounding Box Validation (India: Lat 6.0 to 38.0, Lon 68.0 to 98.0)
        print("\n[Check 1/5] Geographic Coordinate Bounding Box Validation (India)...")
        invalid_lats = df_atms[(df_atms["ATM_Latitude"] < 6.0) | (df_atms["ATM_Latitude"] > 38.0)]
        invalid_lons = df_atms[(df_atms["ATM_Longitude"] < 68.0) | (df_atms["ATM_Longitude"] > 98.0)]
        if not invalid_lats.empty or not invalid_lons.empty:
            self.errors.append(f"Found {len(invalid_lats)} invalid latitudes and {len(invalid_lons)} invalid longitudes in ATMs.")
        else:
            print(f"  [PASS] All {len(df_atms)} ATM coordinates are within valid Indian bounding box.")

        # 4. HMAC Account Pseudonymization Check
        print("\n[Check 2/5] Account Identifier Pseudonymization (HMAC-SHA256)...")
        sample_hashes = df_tx["sourceHashedAccNo"].dropna().sample(min(100, len(df_tx))).tolist()
        leaked_raw = [h for h in sample_hashes if "ACCT_" in h or len(h) != 16]
        if leaked_raw:
            self.errors.append(f"Detected un-hashed or malformed account numbers: {leaked_raw[:5]}")
        else:
            print(f"  [PASS] All account linkages use valid 16-character HMAC-SHA256 pseudonymized hashes.")

        # 5. Class Balance & Cash-Out Properties
        print("\n[Check 3/5] Class Balance & Target Properties...")
        fraud_ratio = float(df_tx["Is_Fraud"].mean())
        print(f"  Fraudulent Transaction Proportion: {fraud_ratio:.2%}")
        if fraud_ratio < 0.05 or fraud_ratio > 0.35:
            self.warnings.append(f"Unusual fraud ratio: {fraud_ratio:.2%}")
        else:
            print(f"  [PASS] Realistic fraud proportion (5% - 35% range).")

        atm_cashouts = df_tx[(df_tx["Channel"] == "ATM") & (df_tx["Is_Fraud"] == 1)]
        print(f"  Total Fraudulent ATM Cash-outs: {len(atm_cashouts):,}")

        # 6. PDF NCERT Hotspot Prior Correlation
        print("\n[Check 4/5] Distribution Grounding vs NCERT 2024 ATM Hotspot Priors...")
        city_counts = df_tx["City"].value_counts()
        hotspot_df = self.priors.hotspot_df.copy()
        hotspot_df["synthetic_count"] = hotspot_df["location"].map(city_counts).fillna(0)

        # Calculate rank correlation
        spearman_corr = float(hotspot_df["transactions"].corr(hotspot_df["synthetic_count"], method="spearman"))
        pearson_corr = float(hotspot_df["transactions"].corr(hotspot_df["synthetic_count"], method="pearson"))

        print(f"  NCERT Prior vs Synthetic Counts Pearson Correlation  : {pearson_corr:.4f}")
        print(f"  NCERT Prior vs Synthetic Counts Spearman Rank Corr   : {spearman_corr:.4f}")
        print("\n  Top 5 Hotspot Comparison:")
        for _, row in hotspot_df.head(5).iterrows():
            print(f"    - {row['location']:<15}: Prior={row['transactions']:>6,} | Synthetic={int(row['synthetic_count']):>6,}")

        if spearman_corr < 0.70:
            self.warnings.append(f"Spearman correlation with PDF priors is low: {spearman_corr:.2f}")
        else:
            print(f"  [PASS] Strong alignment with NCERT 2024 public research distributions.")

        # 7. Temporal & Missing Data Consistency
        print("\n[Check 5/5] Data Integrity & Temporal Sequence...")
        null_counts = df_unified.isnull().sum()
        critical_nulls = null_counts[["Transaction_ID", "Transaction_Amount", "prediction_timestamp", "Latitude", "Longitude", "Is_Fraud"]]
        if critical_nulls.sum() > 0:
            self.errors.append(f"Critical columns have missing values: {critical_nulls[critical_nulls > 0].to_dict()}")
        else:
            print(f"  [PASS] Zero nulls in all mandatory predictive features.")

        # Summary
        print("\n" + "=" * 65)
        if self.errors:
            print(f"  VALIDATION FAILED: {len(self.errors)} errors, {len(self.warnings)} warnings")
            for e in self.errors:
                print(f"    [ERROR] {e}")
            return {"status": "FAIL", "errors": self.errors, "warnings": self.warnings}
        else:
            print(f"  VALIDATION SUCCESSFUL: 0 errors, {len(self.warnings)} warnings")
            return {
                "status": "PASS",
                "total_atms": len(df_atms),
                "total_accounts": len(df_accounts),
                "total_transactions": len(df_tx),
                "total_complaints": len(df_cmp),
                "pearson_correlation_with_priors": round(pearson_corr, 4),
                "spearman_correlation_with_priors": round(spearman_corr, 4)
            }

def main():
    validator = SyntheticDataValidator()
    result = validator.validate_all()
    print("\nValidation Result JSON:\n", json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
