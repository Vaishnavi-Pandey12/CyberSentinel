"""
Public Data Loader for CyberSentinel Synthetic Generator
Loads aggregate statistics from the 2024 NCERT presentation, NCRP cyber-fraud data,
and historical ATM physical crime statistics.
"""
import os
import json
from typing import Dict, Any, List
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIORS_FILE = os.path.join(BASE_DIR, "data", "public", "public_priors.json")

def load_public_priors() -> Dict[str, Any]:
    if not os.path.exists(PRIORS_FILE):
        raise FileNotFoundError(f"Public priors file not found at {PRIORS_FILE}")
    with open(PRIORS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

class PublicDataDistributions:
    def __init__(self):
        self.priors = load_public_priors()
        self._initialize()

    def _initialize(self):
        # 1. ATM Hotspots Table (NCERT 2024)
        hotspot_data = self.priors.get("atm_hotspots_ncert_2024", [])
        self.hotspot_df = pd.DataFrame(hotspot_data)
        
        # Calculate sampling probabilities based on reported transaction counts
        total_tx = self.hotspot_df["transactions"].sum()
        self.hotspot_df["weight"] = self.hotspot_df["transactions"] / total_tx
        self.hotspot_cities = self.hotspot_df["location"].tolist()
        self.hotspot_weights = self.hotspot_df["weight"].to_numpy()
        
        # 2. State-Level Cyber-Fraud Distributions (NCRP)
        state_incidents = self.priors.get("ncrp_state_reported_incidents", {})
        total_ncrp = sum(state_incidents.values())
        self.states = list(state_incidents.keys())
        self.state_weights = np.array([v / total_ncrp for v in state_incidents.values()])
        
        # 3. ATM Physical Crimes 2018-19
        atm_crimes = self.priors.get("historical_atm_physical_crimes_2018_19", {})
        total_crimes = sum(atm_crimes.values())
        self.atm_crime_states = list(atm_crimes.keys())
        self.atm_crime_weights = np.array([v / total_crimes for v in atm_crimes.values()])

        # 4. Security Survey Priors (Delhi Police 2024)
        survey = self.priors.get("delhi_police_atm_security_survey_2024", {})
        self.guard_missing_rate = survey.get("vulnerability_rate_guard_missing", 0.45)
        self.lock_missing_rate = survey.get("vulnerability_rate_lock_missing", 0.58)

    def sample_hotspot_city(self, rng: np.random.Generator) -> Dict[str, Any]:
        """Sample an ATM hotspot city according to the NCERT transaction distribution."""
        idx = rng.choice(len(self.hotspot_cities), p=self.hotspot_weights)
        row = self.hotspot_df.iloc[idx]
        return {
            "city": row["location"],
            "state": row["state"],
            "district": row["district"],
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "rank": int(row["rank"]),
            "transactions_prior": int(row["transactions"])
        }

    def sample_state(self, rng: np.random.Generator) -> str:
        """Sample a state according to NCRP cyber-fraud distribution."""
        return str(rng.choice(self.states, p=self.state_weights))

    def get_all_hotspots(self) -> List[Dict[str, Any]]:
        return self.hotspot_df.to_dict(orient="records")
