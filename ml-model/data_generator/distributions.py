"""
Domain distributions and categorical configurations for CyberSentinel synthetic generation.
"""
from typing import List, Dict, Any
import numpy as np

INDIAN_BANKS = [
    'State Bank of India', 'HDFC Bank', 'ICICI Bank', 'Punjab National Bank',
    'Axis Bank', 'Bank of Baroda', 'Kotak Mahindra Bank', 'Canara Bank',
    'Union Bank of India', 'IndusInd Bank'
]
BANK_WEIGHTS = [0.28, 0.18, 0.14, 0.10, 0.08, 0.07, 0.05, 0.04, 0.03, 0.03]

CHANNELS = ['ATM', 'UPI', 'Online', 'POS/Card', 'Branch']
CHANNEL_WEIGHTS_NORMAL = [0.25, 0.45, 0.18, 0.08, 0.04]
CHANNEL_WEIGHTS_FRAUD = [0.55, 0.30, 0.10, 0.04, 0.01]

LOCATION_TYPES = [
    'Commercial_Area', 'Market', 'Shopping_Mall', 'Railway_Station',
    'Bus_Stand', 'Residential', 'Highway', 'Educational_Area', 'Airport', 'Other'
]
LOCATION_TYPE_WEIGHTS = [0.25, 0.22, 0.15, 0.12, 0.08, 0.08, 0.04, 0.03, 0.02, 0.01]

FRAUD_CATEGORIES = [
    'ATM Skimming',
    'Card Cloning',
    'Unauthorized ATM Cash-Out',
    'UPI Phishing & Impersonation',
    'OTP / SIM-Swap Fraud',
    'Investment / Task Scam',
    'Vishing / Customer Care Scam'
]
FRAUD_CATEGORY_WEIGHTS = [0.22, 0.20, 0.24, 0.15, 0.10, 0.05, 0.04]

ID_TYPES = ['Driving License', 'Voter ID', 'Passport', 'Ration Card', 'Govt Employee ID']
GENDERS = ['Male', 'Female', 'Other']
GENDER_WEIGHTS = [0.62, 0.37, 0.01]

COMPLAINT_CHANNELS = ['NCRP 1930 Portal', 'Police Station', 'Bank Helpline', 'Cyber Cell Desk', 'Online Grievance']

def sample_normal_amount(rng: np.random.Generator, channel: str) -> float:
    if channel == 'ATM':
        common_denominations = [500, 1000, 2000, 3000, 4000, 5000, 8000, 10000, 15000, 20000]
        denom_probs = [0.10, 0.15, 0.20, 0.10, 0.10, 0.18, 0.07, 0.06, 0.03, 0.01]
        return float(rng.choice(common_denominations, p=denom_probs))
    elif channel == 'UPI':
        amt = rng.exponential(scale=1200) + 50
        return float(np.clip(round(amt, 2), 50.0, 50000.0))
    elif channel == 'Online':
        amt = rng.exponential(scale=4500) + 200
        return float(np.clip(round(amt, 2), 100.0, 100000.0))
    elif channel == 'POS/Card':
        amt = rng.exponential(scale=1800) + 100
        return float(np.clip(round(amt, 2), 100.0, 25000.0))
    else:
        amt = rng.exponential(scale=25000) + 1000
        return float(np.clip(round(amt, 2), 500.0, 500000.0))

def sample_fraud_amount(rng: np.random.Generator, channel: str, is_cashout: bool = False) -> float:
    if is_cashout or channel == 'ATM':
        amounts = [10000, 20000, 25000, 35000, 40000, 45000, 50000]
        probs = [0.15, 0.25, 0.15, 0.15, 0.15, 0.08, 0.07]
        return float(rng.choice(amounts, p=probs))
    elif channel == 'UPI':
        return float(rng.choice([15000, 25000, 49000, 75000, 95000]))
    else:
        return float(rng.choice([50000, 80000, 120000, 200000, 350000]))
