import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

def cluster_interdiction_zones(locations_df: pd.DataFrame, eps_km: float = 1.5, min_samples: int = 2) -> pd.DataFrame:
    """
    Groups spatial coordinates of ATMs/Hotspots into high-probability 'Interdiction Zones'
    using DBSCAN density-based clustering with Haversine metric.

    Parameters:
        locations_df (pd.DataFrame): DataFrame containing 'latitude' and 'longitude' columns.
        eps_km (float): Max distance radius in kilometers for cluster neighborhood (default 1.5km).
        min_samples (int): Minimum number of ATMs required to form a dense interdiction zone.

    Returns:
        pd.DataFrame: Original DataFrame enriched with 'cluster_id' and 'is_interdiction_zone'.
    """
    df = locations_df.copy()
    if df.empty or 'latitude' not in df.columns or 'longitude' not in df.columns:
        return df

    # Convert degrees to radians for Haversine metric
    coords_rad = np.radians(df[['latitude', 'longitude']].values)

    # Earth radius ~ 6371 km
    kms_per_radian = 6371.0
    epsilon = eps_km / kms_per_radian

    db = DBSCAN(eps=epsilon, min_samples=min_samples, metric='haversine')
    df['cluster_id'] = db.fit_predict(coords_rad)
    df['is_interdiction_zone'] = df['cluster_id'].apply(lambda cid: 1 if cid >= 0 else 0)

    return df

if __name__ == "__main__":
    # Test example with sample Indian ATM coordinates
    sample_data = pd.DataFrame([
        {"location_id": "ATM-104", "location_name": "MG Road ATM Cluster", "latitude": 16.5062, "longitude": 80.6480},
        {"location_id": "ATM-221", "location_name": "Benz Circle Hub", "latitude": 16.5044, "longitude": 80.6558},
        {"location_id": "ATM-312", "location_name": "University Zone", "latitude": 16.5062, "longitude": 80.6210},
        {"location_id": "ATM-087", "location_name": "KPHB Metro ATM", "latitude": 17.4856, "longitude": 78.3918},
        {"location_id": "ATM-176", "location_name": "Gachibowli Financial", "latitude": 17.4421, "longitude": 78.3489},
    ])

    result = cluster_interdiction_zones(sample_data, eps_km=2.0, min_samples=2)
    print("DBSCAN Spatial Interdiction Clustering Result:")
    print(result[['location_id', 'location_name', 'cluster_id', 'is_interdiction_zone']])
