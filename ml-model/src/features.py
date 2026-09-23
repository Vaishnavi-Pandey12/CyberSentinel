"""
CyberSentinel Feature Engineering Pipeline
Implements strict leakage-safe spatial, temporal, historical rolling, and ATM feature extraction.
"""
import os
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Any

STATE_MAPPING = {
    'Delhi': 1, 'Rajasthan': 2, 'West Bengal': 3, 'Bihar': 4,
    'Uttar Pradesh': 5, 'Jharkhand': 6, 'Haryana': 7, 'Maharashtra': 8,
    'Gujarat': 9, 'Karnataka': 10, 'Telangana': 11, 'Tamil Nadu': 12,
    'Madhya Pradesh': 13, 'Andhra Pradesh': 14, 'Kerala': 15, 'Odisha': 16,
    'Punjab': 17, 'Chhattisgarh': 18, 'Uttarakhand': 19, 'Assam': 20
}

CHANNEL_MAPPING = {'ATM': 1, 'UPI': 2, 'Online': 3, 'POS/Card': 4, 'Branch': 5}
TXN_TYPE_MAPPING = {'Debit': 1, 'Credit': 2, 'Transfer': 3}
LOCATION_TYPE_MAPPING = {
    'Commercial_Area': 1, 'Market': 2, 'Shopping_Mall': 3, 'Railway_Station': 4,
    'Bus_Stand': 5, 'Residential': 6, 'Highway': 7, 'Educational_Area': 8,
    'Airport': 9, 'Other': 10
}
ATM_TYPE_MAPPING = {'Bank-Owned': 1, 'White-Label': 2, 'Brown-Label': 3, 'Online/Digital': 4}

FEATURE_COLUMNS = [
    # Spatial / Geographic
    'Latitude', 'Longitude', 'State_Encoded', 'Urban_Rural_Encoded',
    'Location_Type_Encoded', 'Nearby_ATM_Count', 'Local_Fraud_Density',

    # ATM Hardware & Security
    'ATM_Type_Encoded', 'ATM_Is_Onsite', 'ATM_Is_Indoor', 'CCTV_Available',
    'Security_Guard_Present', 'Shutter_Lock_Present', 'ATM_Is_Active',

    # Transaction Characteristics
    'Transaction_Amount', 'log_Transaction_Amount', 'Channel_Encoded',
    'Transaction_Type_Encoded', 'LoginAttempts', 'TransactionDuration', 'log_AccountBalance',

    # Temporal & Cyclical
    'Hour', 'Day_of_Week', 'Is_Weekend', 'Is_Night', 'hour_sin', 'hour_cos', 'day_sin', 'day_cos',

    # Leakage-Safe Historical Rolling Features
    'Complaint_Count_7D', 'Complaint_Count_30D', 'Complaint_Count_90D',
    'Fraud_Count_7D', 'Fraud_Count_30D', 'Fraud_Count_90D',
    'ATM_Fraud_Count_30D', 'Location_Fraud_Count_30D',
    'Total_Loss_7D', 'Total_Loss_30D', 'Total_Loss_90D', 'Average_Loss_30D',
    'Withdrawal_Count_7D', 'Withdrawal_Count_30D', 'Withdrawal_Amount_30D'
]

def extract_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    data = df.copy()

    # Temporal features
    dt = pd.to_datetime(data['prediction_timestamp'])
    data['Hour'] = dt.dt.hour
    data['Day_of_Week'] = dt.dt.dayofweek
    data['hour_sin'] = np.sin(2 * np.pi * data['Hour'] / 24.0)
    data['hour_cos'] = np.cos(2 * np.pi * data['Hour'] / 24.0)
    data['day_sin'] = np.sin(2 * np.pi * data['Day_of_Week'] / 7.0)
    data['day_cos'] = np.cos(2 * np.pi * data['Day_of_Week'] / 7.0)
    data['Is_Weekend'] = (data['Day_of_Week'] >= 5).astype(int)
    data['Is_Night'] = ((data['Hour'] >= 22) | (data['Hour'] <= 5)).astype(int)

    # Scaled / Log features
    data['log_Transaction_Amount'] = np.log1p(np.maximum(0, data['Transaction_Amount'].astype(float)))
    balance = data['AccountBalance'].astype(float) if 'AccountBalance' in data.columns else 10000.0
    data['log_AccountBalance'] = np.log1p(np.maximum(0, balance))

    # Categorical encodings
    data['State_Encoded'] = data['State'].map(lambda s: STATE_MAPPING.get(str(s), 0))
    data['Channel_Encoded'] = data['Channel'].map(lambda c: CHANNEL_MAPPING.get(str(c), 0))
    data['Transaction_Type_Encoded'] = data['Transaction_Type'].map(lambda t: TXN_TYPE_MAPPING.get(str(t), 0))
    data['Location_Type_Encoded'] = data['Location_Type'].map(lambda l: LOCATION_TYPE_MAPPING.get(str(l), 0))
    data['ATM_Type_Encoded'] = data['ATM_Type'].map(lambda a: ATM_TYPE_MAPPING.get(str(a), 0))
    data['Urban_Rural_Encoded'] = (data['Urban_Rural'] == 'Urban').astype(int)

    data['ATM_Is_Onsite'] = (data['ATM_Onsite_Offsite'] == 'Onsite').astype(int)
    data['ATM_Is_Indoor'] = (data['ATM_Indoor_Outdoor'] == 'Indoor').astype(int)
    data['ATM_Is_Active'] = (data['ATM_Operating_Status'] == 'Active').astype(int)
    data['CCTV_Available'] = data['CCTV_Available'].astype(int)
    data['Security_Guard_Present'] = data['Security_Guard_Present'].astype(int) if 'Security_Guard_Present' in data.columns else 0
    data['Shutter_Lock_Present'] = data['Shutter_Lock_Present'].astype(int) if 'Shutter_Lock_Present' in data.columns else 0

    for col in FEATURE_COLUMNS:
        if col not in data.columns:
            data[col] = 0.0
        data[col] = data[col].fillna(0.0)

    X = data[FEATURE_COLUMNS].copy()
    y_hotspot = data['future_cashout'].copy() if 'future_cashout' in data.columns else None
    y_volume = data['future_withdrawal_volume'].copy() if 'future_withdrawal_volume' in data.columns else None

    return X, y_hotspot, y_volume

def load_feature_splits(processed_dir: str):
    df_train = pd.read_csv(os.path.join(processed_dir, 'train_data.csv'))
    df_val = pd.read_csv(os.path.join(processed_dir, 'val_data.csv'))
    df_test = pd.read_csv(os.path.join(processed_dir, 'test_data.csv'))

    X_train, y_train_hotspot, y_train_volume = extract_features(df_train)
    X_val, y_val_hotspot, y_val_volume = extract_features(df_val)
    X_test, y_test_hotspot, y_test_volume = extract_features(df_test)

    return (
        (X_train, y_train_hotspot, y_train_volume),
        (X_val, y_val_hotspot, y_val_volume),
        (X_test, y_test_hotspot, y_test_volume),
        FEATURE_COLUMNS
    )

