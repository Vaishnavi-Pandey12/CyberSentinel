"""
CyberSentinel Preprocessing Engine
Computes chronological rolling window aggregations (7D, 30D, 90D) and per-ATM forward lookahead targets
from data/synthetic/synthetic_historical_ml_dataset.csv.
"""
import os
import numpy as np
import pandas as pd

def preprocess_pipeline(raw_csv_path: str, output_dir: str, future_window_hours: int = 24):
    print(f"Loading dataset from: {raw_csv_path}")
    df = pd.read_csv(raw_csv_path)

    # 1. Parse and sort chronologically
    df['prediction_timestamp'] = pd.to_datetime(df['prediction_timestamp'])
    df = df.sort_values('prediction_timestamp').reset_index(drop=True)

    n = len(df)
    times = df['prediction_timestamp'].to_numpy(dtype='datetime64[ns]')
    amounts = df['Transaction_Amount'].to_numpy(dtype=float)
    is_fraud = df['Is_Fraud'].to_numpy(dtype=int)
    is_withdrawal = (df['Channel'] == 'ATM').to_numpy(dtype=int)
    is_fraud_withdrawal = (is_fraud & is_withdrawal)

    # 2. Historical Rolling Aggregations (Strictly using records before timestamp t)
    print("Computing leakage-safe historical rolling features (7D, 30D, 90D)...")
    comp_7d = np.zeros(n, dtype=int)
    comp_30d = np.zeros(n, dtype=int)
    comp_90d = np.zeros(n, dtype=int)
    fraud_7d = np.zeros(n, dtype=int)
    fraud_30d = np.zeros(n, dtype=int)
    fraud_90d = np.zeros(n, dtype=int)
    loss_7d = np.zeros(n, dtype=float)
    loss_30d = np.zeros(n, dtype=float)
    loss_90d = np.zeros(n, dtype=float)
    wd_count_7d = np.zeros(n, dtype=int)
    wd_count_30d = np.zeros(n, dtype=int)
    wd_amt_30d = np.zeros(n, dtype=float)

    start_7d, start_30d, start_90d = 0, 0, 0
    for i in range(n):
        curr_t = times[i]
        t_7d = curr_t - np.timedelta64(7, 'D')
        t_30d = curr_t - np.timedelta64(30, 'D')
        t_90d = curr_t - np.timedelta64(90, 'D')

        while start_7d < i and times[start_7d] < t_7d: start_7d += 1
        while start_30d < i and times[start_30d] < t_30d: start_30d += 1
        while start_90d < i and times[start_90d] < t_90d: start_90d += 1

        if start_7d < i:
            fraud_7d[i] = is_fraud[start_7d:i].sum()
            loss_7d[i] = (amounts[start_7d:i] * is_fraud[start_7d:i]).sum()
            wd_count_7d[i] = is_withdrawal[start_7d:i].sum()
            comp_7d[i] = fraud_7d[i]

        if start_30d < i:
            fraud_30d[i] = is_fraud[start_30d:i].sum()
            loss_30d[i] = (amounts[start_30d:i] * is_fraud[start_30d:i]).sum()
            wd_count_30d[i] = is_withdrawal[start_30d:i].sum()
            wd_amt_30d[i] = (amounts[start_30d:i] * is_withdrawal[start_30d:i]).sum()
            comp_30d[i] = fraud_30d[i]

        if start_90d < i:
            fraud_90d[i] = is_fraud[start_90d:i].sum()
            loss_90d[i] = (amounts[start_90d:i] * is_fraud[start_90d:i]).sum()
            comp_90d[i] = fraud_90d[i]

    df['Complaint_Count_7D'] = comp_7d
    df['Complaint_Count_30D'] = comp_30d
    df['Complaint_Count_90D'] = comp_90d
    df['Fraud_Count_7D'] = fraud_7d
    df['Fraud_Count_30D'] = fraud_30d
    df['Fraud_Count_90D'] = fraud_90d
    df['Total_Loss_7D'] = np.round(loss_7d, 2)
    df['Total_Loss_30D'] = np.round(loss_30d, 2)
    df['Total_Loss_90D'] = np.round(loss_90d, 2)
    df['Average_Loss_30D'] = np.round(loss_30d / np.maximum(1, fraud_30d), 2)
    df['Withdrawal_Count_7D'] = wd_count_7d
    df['Withdrawal_Count_30D'] = wd_count_30d
    df['Withdrawal_Amount_30D'] = np.round(wd_amt_30d, 2)
    df['ATM_Fraud_Count_30D'] = fraud_30d
    df['Location_Fraud_Count_30D'] = fraud_30d
    df['Local_Fraud_Density'] = np.round(fraud_30d / (wd_count_30d + 1), 4)
    df['Nearby_ATM_Count'] = 12

    # 3. Target Variables: Forward Lookahead evaluated per ATM / Location
    print(f"Computing per-location forward targets (next {future_window_hours}h)...")
    future_cashouts = np.zeros(n, dtype=int)
    future_volumes = np.zeros(n, dtype=float)

    df['entity_key'] = df['ATM_ID'].where(df['ATM_ID'] != 'NONE', df['City'])

    for _, group in df.groupby('entity_key', sort=False):
        indices = group.index.to_numpy()
        g_times = times[indices]
        g_fraud_wd = is_fraud_withdrawal[indices]
        g_amt = amounts[indices]
        g_is_wd = is_withdrawal[indices]
        gn = len(indices)
        
        end_idx = 0
        for i in range(gn):
            curr_t = g_times[i]
            window_end = curr_t + np.timedelta64(future_window_hours, 'h')
            while end_idx < gn and g_times[end_idx] <= window_end:
                end_idx += 1

            if i + 1 < end_idx:
                future_cashouts[indices[i]] = int(g_fraud_wd[i + 1:end_idx].sum() > 0)
                future_volumes[indices[i]] = float((g_amt[i + 1:end_idx] * g_is_wd[i + 1:end_idx]).sum())

    df['future_cashout'] = future_cashouts
    df['future_withdrawal_volume'] = np.round(future_volumes, 2)
    df.drop(columns=['entity_key'], inplace=True)
    df['prediction_timestamp'] = df['prediction_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # 4. Chronological Train (70%), Val (15%), Test (15%) Split
    n_train = int(n * 0.70)
    n_val = int(n * 0.85)

    train_df = df.iloc[:n_train].copy()
    val_df = df.iloc[n_train:n_val].copy()
    test_df = df.iloc[n_val:].copy()

    os.makedirs(output_dir, exist_ok=True)
    train_df.to_csv(os.path.join(output_dir, 'train_data.csv'), index=False)
    val_df.to_csv(os.path.join(output_dir, 'val_data.csv'), index=False)
    test_df.to_csv(os.path.join(output_dir, 'test_data.csv'), index=False)

    print(f"\n[OK] Preprocessing completed:")
    print(f"  Train : {len(train_df):,} records (Cashout rate: {train_df['future_cashout'].mean():.2%})")
    print(f"  Val   : {len(val_df):,} records (Cashout rate: {val_df['future_cashout'].mean():.2%})")
    print(f"  Test  : {len(test_df):,} records (Cashout rate: {test_df['future_cashout'].mean():.2%})")

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    synth_csv = os.path.join(base_dir, 'data', 'synthetic', 'synthetic_historical_ml_dataset.csv')
    processed_dir = os.path.join(base_dir, 'data', 'processed')
    preprocess_pipeline(synth_csv, processed_dir)
    