import os
import numpy as np
import pandas as pd

# City-to-Coordinate Mapping for the 76 Indian Cities in the dataset
CITY_COORDINATES = {
    'Agra':                         (27.1767,  78.0081),
    'Ahmedabad':                    (23.0225,  72.5714),
    'Ajmer':                        (26.4499,  74.6399),
    'Aligarh':                      (27.8974,  78.0880),
    'Amritsar':                     (31.6340,  74.8723),
    'Barpeta Road, Assam':          (26.4983,  90.9785),
    'Belagavi':                     (15.8497,  74.4977),
    'Bengaluru':                    (12.9716,  77.5946),
    'Bhavnagar':                    (21.7645,  72.1519),
    'Bhilai':                       (21.1938,  81.3509),
    'Bhopal':                       (23.2599,  77.4126),
    'Bikaner':                      (28.0229,  73.3119),
    'Chandigarh':                   (30.7333,  76.7794),
    'Chennai':                      (13.0827,  80.2707),
    'Chizami, Nagaland':            (25.6540,  94.0804),
    'Coimbatore':                   (11.0168,  76.9558),
    'Dehradun':                     (30.3165,  78.0322),
    'Delhi':                        (28.6139,  77.2090),
    'Dharnai, Bihar':               (25.1940,  85.9060),
    'Durgapur':                     (23.5204,  87.3119),
    'Faridabad':                    (28.4089,  77.3178),
    'Gorakhpur':                    (26.7606,  83.3732),
    'Guntur':                       (16.3067,  80.4365),
    'Guwahati':                     (26.1445,  91.7362),
    'Hivre Bazar, Maharashtra':     (19.7170,  74.7170),
    'Hyderabad':                    (17.3850,  78.4867),
    'Indore':                       (22.7196,  75.8577),
    'Jaipur':                       (26.9124,  75.7873),
    'Jalandhar':                    (31.3260,  75.5762),
    'Jhansi':                       (25.4484,  78.5685),
    'Jodhpur':                      (26.2389,  73.0243),
    'Kanpur':                       (26.4499,  80.3319),
    'Khimsar, Rajasthan':           (27.0756,  72.7800),
    'Kochi':                        ( 9.9312,  76.2673),
    'Kokkrebellur, Karnataka':      (12.6220,  77.0280),
    'Kolhapur':                     (16.7050,  74.2433),
    'Kolkata':                      (22.5726,  88.3639),
    'Ladpura, Rajasthan':           (25.1503,  75.8504),
    'Longwa, Nagaland':             (26.5600,  95.2900),
    'Lucknow':                      (26.8467,  80.9462),
    'Ludhiana':                     (30.9010,  75.8573),
    'Madurai':                      ( 9.9252,  78.1198),
    'Malana, Himachal Pradesh':     (32.0670,  77.2640),
    'Mawlynnong, Meghalaya':        (25.2020,  91.9160),
    'Mumbai':                       (19.0760,  72.8777),
    'Muzaffarpur':                  (26.1209,  85.3647),
    'Mysuru':                       (12.2958,  76.6394),
    'Nagepalle, Andhra Pradesh':    (14.4980,  77.7790),
    'Nagpur':                       (21.1458,  79.0882),
    'Nashik':                       (19.9975,  73.7898),
    'Nellore':                      (14.4426,  79.9865),
    'Panaji':                       (15.4909,  73.8278),
    'Patna':                        (25.5941,  85.1376),
    'Piplantri, Rajasthan':         (25.5073,  73.8021),
    'Pochampally, Telangana':       (17.3570,  78.7070),
    'Puducherry':                   (11.9416,  79.8083),
    'Pune':                         (18.5204,  73.8567),
    'Punsari, Gujarat':             (23.5780,  73.0800),
    'Raipur':                       (21.2514,  81.6296),
    'Rajkot':                       (22.3039,  70.8022),
    'Ralegan Siddhi, Maharashtra':  (18.7430,  74.5460),
    'Ranchi':                       (23.3441,  85.3096),
    'Rourkela':                     (22.2604,  84.8536),
    'Sangli':                       (16.8524,  74.5815),
    'Shimla':                       (31.1048,  77.1734),
    'Siliguri':                     (26.7271,  88.3953),
    'Sittilingi, Tamil Nadu':       (11.8960,  78.2300),
    'Surat':                        (21.1702,  72.8311),
    'Thiruvananthapuram':           ( 8.5241,  76.9366),
    'Tirupati':                     (13.6288,  79.4192),
    'Ujjain':                       (23.1765,  75.7885),
    'Vadodara':                     (22.3072,  73.1812),
    'Varanasi':                     (25.3176,  82.9739),
    'Vijayawada':                   (16.5062,  80.6480),
    'Visakhapatnam':                (17.6868,  83.2185),
    'Warangal':                     (17.9784,  79.5941),
}

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the Great Circle (Haversine) distance between two points in km."""
    R = 6371.0  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def assign_crime_category(row):
    """
    Categorize transaction for Indian banking context.
    Handles channels: ATM, UPI, Online, POS/Card, Branch.
    Thresholds are in INR (Indian Rupees).
    """
    channel  = row['Channel']
    txn_type = row['TransactionType']
    amount   = row['TransactionAmount']
    login    = row['LoginAttempts']
    duration = row['TransactionDuration']
    is_debit = (txn_type == 'Debit')

    # ATM cash-out: high INR amount or repeated login failures (card skimming / cloning)
    if channel == 'ATM' and is_debit and (amount > 10000 or login > 1):
        return 'suspicious_cash_withdrawal'

    # UPI fraud: SIM-swap, vishing, OTP theft — login anomaly or large debit
    if channel == 'UPI' and (login > 1 or (is_debit and amount > 50000)):
        return 'unusual_online_activity'

    # Online banking anomaly: malware, credential stuffing, OTP bypass
    if channel == 'Online' and (login > 1 or duration > 150):
        return 'unusual_online_activity'

    # POS/Card skimming or card-not-present fraud
    if channel == 'POS/Card' and is_debit and (amount > 20000 or login > 1):
        return 'suspicious_cash_withdrawal'

    # High-value wire / RTGS / NEFT transfer
    if amount > 100000:
        return 'high_value_transfer'

    return 'routine_transaction'

def preprocess_pipeline(raw_csv_path, output_dir, future_window_hours=3, train_ratio=0.80):
    print(f"Reading raw dataset from: {raw_csv_path}")
    df = pd.read_csv(raw_csv_path)

    try:
        from tqdm import tqdm
        tqdm.pandas(desc="  Crime category")
        HAS_TQDM = True
    except ImportError:
        HAS_TQDM = False
        print("  [INFO] tqdm not installed — install it via 'pip install tqdm' for progress bars.")

    # Clean BOM or unexpected column names
    df.columns = [c.replace('\ufeff', '').strip() for c in df.columns]

    # Parse prediction_time — dayfirst=True handles DD/MM/YYYY (Indian format)
    print("Parsing timestamps (dayfirst=True for Indian date format)...")
    df['prediction_time'] = pd.to_datetime(df['TransactionDate'], format='mixed', dayfirst=True)

    # STEP 1: Sort Chronologically Before Any Operation
    print("Sorting by timestamp...")
    df = df.sort_values('prediction_time').reset_index(drop=True)

    # 1. Location ID Mapping
    unique_cities = sorted(df['Location'].unique())
    city_to_loc_id = {city: f"LOC_{i+1:03d}" for i, city in enumerate(unique_cities)}
    df['location_id'] = df['Location'].map(city_to_loc_id)

    # 2. Coordinates Mapping — warn on missing cities
    unmapped = [c for c in unique_cities if c not in CITY_COORDINATES]
    if unmapped:
        print(f"  [WARN] {len(unmapped)} cities not in coordinate map (defaulting to 0.0,0.0): {unmapped}")
    df['latitude']  = df['Location'].map(lambda loc: CITY_COORDINATES.get(str(loc), (0.0, 0.0))[0])
    df['longitude'] = df['Location'].map(lambda loc: CITY_COORDINATES.get(str(loc), (0.0, 0.0))[1])

    # 3. Time Features
    df['hour']        = df['prediction_time'].dt.hour
    df['day_of_week'] = df['prediction_time'].dt.dayofweek

    # 4. Crime Category & Amount
    print("Assigning crime categories...")
    if HAS_TQDM:
        df['crime_category'] = df.progress_apply(assign_crime_category, axis=1)  # type: ignore[operator]
    else:
        df['crime_category'] = df.apply(assign_crime_category, axis=1)
    df['transaction_amount'] = df['TransactionAmount'].astype(float)

    # 5. ATM Debit withdrawal flag
    df['is_withdrawal'] = (df['Channel'] == 'ATM') & (df['TransactionType'] == 'Debit')
    df['is_high_risk']  = df['is_withdrawal'] | (df['crime_category'] != 'routine_transaction')

    # ── STEP 2 & 3: Historical Location Features & Hotspot Density ─────────────
    print("\n[Step 2/4] Location rolling features (24h tx count, 30-day density, historical risk)...")
    recent_txn_counts         = np.zeros(len(df), dtype=int)
    recent_withdrawal_counts  = np.zeros(len(df), dtype=int)
    historical_location_risks = np.zeros(len(df), dtype=float)
    location_density_30d      = np.zeros(len(df), dtype=int)

    location_groups = list(df.groupby('location_id', sort=False))
    loc_iter = tqdm(location_groups, desc="  Locations", unit="loc") if HAS_TQDM else location_groups
    for loc_id, group in loc_iter:
        times      = group['prediction_time'].to_numpy(dtype='datetime64[ns]')
        withdrawals= group['is_withdrawal'].to_numpy().astype(int)
        high_risks = group['is_high_risk'].to_numpy().astype(int)
        indices    = group.index.values
        n          = len(group)
        start_24h  = 0
        start_30d  = 0
        cum_total  = 0
        cum_risk   = 0

        for i in range(n):
            curr_t     = times[i]
            window_24h = curr_t - np.timedelta64(24, 'h')
            window_30d = curr_t - np.timedelta64(30, 'D')

            while start_24h < i and times[start_24h] < window_24h:
                start_24h += 1
            while start_30d < i and times[start_30d] < window_30d:
                start_30d += 1

            if start_24h < i:
                recent_txn_counts[indices[i]]        = i - start_24h
                recent_withdrawal_counts[indices[i]] = withdrawals[start_24h:i].sum()
            if start_30d < i:
                location_density_30d[indices[i]] = withdrawals[start_30d:i].sum()

            cum_total += 1
            cum_risk  += high_risks[i]
            historical_location_risks[indices[i]] = round(cum_risk / cum_total, 4)

    df['recent_txn_count']        = recent_txn_counts
    df['recent_withdrawal_count'] = recent_withdrawal_counts
    df['historical_location_risk']= historical_location_risks
    df['location_density_30d']    = location_density_30d

    # ── STEP 2 & 3: Account-Level Trailing Features & Distance/Velocity ────────
    print("\n[Step 3/4] Account trailing features (past 1h/24h withdrawals, distance & velocity)...")
    withdrawals_past_1h     = np.zeros(len(df), dtype=int)
    withdrawals_past_24h    = np.zeros(len(df), dtype=int)
    minutes_since_last_txn  = np.full(len(df), 9999.0, dtype=float)
    dist_from_last_txn_km   = np.zeros(len(df), dtype=float)
    distances_to_recent_wd  = np.zeros(len(df), dtype=float)

    account_groups = list(df.groupby('AccountID', sort=False))
    acc_iter = tqdm(account_groups, desc="  Accounts", unit="acc") if HAS_TQDM else account_groups
    for acc_id, group in acc_iter:
        times      = group['prediction_time'].to_numpy(dtype='datetime64[ns]')
        withdrawals= group['is_withdrawal'].to_numpy().astype(int)
        lats       = group['latitude'].to_numpy()
        lngs       = group['longitude'].to_numpy()
        indices    = group.index.values
        n          = len(group)
        start_1h   = 0
        start_24h  = 0
        last_wd_lat= None
        last_wd_lng= None

        for i in range(n):
            curr_t = times[i]
            t_1h   = curr_t - np.timedelta64(1, 'h')
            t_24h  = curr_t - np.timedelta64(24, 'h')

            while start_1h  < i and times[start_1h]  < t_1h:
                start_1h  += 1
            while start_24h < i and times[start_24h] < t_24h:
                start_24h += 1

            if start_1h  < i:
                withdrawals_past_1h[indices[i]]  = withdrawals[start_1h:i].sum()
            if start_24h < i:
                withdrawals_past_24h[indices[i]] = withdrawals[start_24h:i].sum()

            if i > 0:
                diff_sec = (curr_t - times[i-1]) / np.timedelta64(1, 's')
                minutes_since_last_txn[indices[i]] = round(diff_sec / 60.0, 2)
                dist_from_last_txn_km[indices[i]]  = round(
                    haversine_distance(lats[i], lngs[i], lats[i-1], lngs[i-1]), 2)

            if last_wd_lat is not None:
                distances_to_recent_wd[indices[i]] = round(
                    haversine_distance(lats[i], lngs[i], last_wd_lat, last_wd_lng), 2)

            if withdrawals[i] == 1:
                last_wd_lat = lats[i]
                last_wd_lng = lngs[i]

    df['withdrawals_past_1h']             = withdrawals_past_1h
    df['withdrawals_past_24h']            = withdrawals_past_24h
    df['minutes_since_last_txn']          = minutes_since_last_txn
    df['dist_from_last_txn_km']           = dist_from_last_txn_km
    df['distance_to_recent_withdrawal_km']= distances_to_recent_wd

    # ── STEP 4: Target Variable (Forward Lookahead Window T -> T + 3h) ─────────
    print("\n[Step 4/4] Forward lookahead target variable (withdrawal_occurred in next 3h)...")
    withdrawal_targets = np.zeros(len(df), dtype=int)

    loc_iter2 = tqdm(location_groups, desc="  Target window", unit="loc") if HAS_TQDM else location_groups
    for loc_id, group in loc_iter2:
        times      = group['prediction_time'].to_numpy(dtype='datetime64[ns]')
        withdrawals= group['is_withdrawal'].to_numpy().astype(int)
        indices    = group.index.values
        n          = len(group)
        end_idx    = 0

        for i in range(n):
            curr_t     = times[i]
            window_end = curr_t + np.timedelta64(future_window_hours, 'h')

            while end_idx < n and times[end_idx] <= window_end:
                end_idx += 1

            if i + 1 < end_idx:
                if withdrawals[i + 1:end_idx].sum() > 0:
                    withdrawal_targets[indices[i]] = 1

    df['withdrawal_occurred'] = withdrawal_targets

    # Additional raw fields to preserve
    df['login_attempts']       = df['LoginAttempts'].astype(int)
    df['transaction_duration'] = df['TransactionDuration'].astype(float)
    df['customer_age']         = df['CustomerAge'].astype(int)
    df['account_balance']      = df['AccountBalance'].astype(float)

    # Select final columns in exact order
    final_columns = [
        'location_id', 'latitude', 'longitude', 'prediction_time', 'crime_category',
        'transaction_amount', 'recent_txn_count', 'recent_withdrawal_count',
        'distance_to_recent_withdrawal_km', 'dist_from_last_txn_km', 'minutes_since_last_txn',
        'withdrawals_past_1h', 'withdrawals_past_24h', 'location_density_30d',
        'historical_location_risk', 'login_attempts', 'transaction_duration',
        'customer_age', 'account_balance', 'hour', 'day_of_week', 'withdrawal_occurred'
    ]

    processed_df = df[final_columns].copy()
    processed_df['prediction_time'] = processed_df['prediction_time'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Chronological Train (80%) and Test (20%) Split
    n_total   = len(processed_df)
    train_end = int(n_total * train_ratio)

    train_df = processed_df.iloc[:train_end].copy()
    test_df = processed_df.iloc[train_end:].copy()

    os.makedirs(output_dir, exist_ok=True)
    full_path = os.path.join(output_dir, 'training_data.csv')
    train_path = os.path.join(output_dir, 'train_data.csv')
    test_path = os.path.join(output_dir, 'test_data.csv')

    processed_df.to_csv(full_path, index=False)
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path,  index=False)

    print(f"\n{'='*55}")
    print(f"  Preprocessing & Data Splitting Complete")
    print(f"{'='*55}")
    print(f"  Full Dataset  : {len(processed_df):>8,} records  ->  {full_path}")
    print(f"  Train (80%)   : {len(train_df):>8,} records  ->  {train_path}")
    print(f"  Test  (20%)   : {len(test_df):>8,} records  ->  {test_path}")
    print(f"{'='*55}\n")

if __name__ == '__main__':
    base_dir      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir       = os.path.join(base_dir, 'data', 'raw')
    raw_path      = os.path.join(raw_dir, 'indian_bank_transactions.csv')
    
    if not os.path.exists(raw_path) and os.path.exists(raw_dir):
        csv_files = [f for f in os.listdir(raw_dir) if f.endswith('.csv')]
        if csv_files:
            raw_path = os.path.join(raw_dir, csv_files[0])
            print(f"Default raw file not found. Auto-detected raw file: {raw_path}")

    processed_dir = os.path.join(base_dir, 'data', 'processed')
    preprocess_pipeline(raw_path, processed_dir, train_ratio=0.80)