import numpy as np
from sklearn.cluster import DBSCAN
from typing import List, Dict, Any

def apply_spatial_dbscan(predictions: List[Dict[str, Any]], eps_km: float = 2.0, min_samples: int = 2) -> List[Dict[str, Any]]:
    """
    Applies DBSCAN clustering on prediction items using geographic coordinates.
    Annotates each prediction item with 'cluster_id' and 'is_interdiction_zone'.
    """
    if not predictions:
        return predictions

    valid_items = []
    coords = []

    for item in predictions:
        lat = item.get("latitude")
        lng = item.get("longitude")
        if lat is not None and lng is not None and lat != 0 and lng != 0:
            valid_items.append(item)
            coords.append([lat, lng])
        else:
            item["cluster_id"] = -1
            item["is_interdiction_zone"] = False

    if len(valid_items) < min_samples:
        for item in predictions:
            item.setdefault("cluster_id", -1)
            item.setdefault("is_interdiction_zone", False)
        return predictions

    # Convert coordinates from degrees to radians for Haversine metric
    coords_rad = np.radians(np.array(coords))

    # Earth radius approx 6371 km
    kms_per_radian = 6371.0
    epsilon = eps_km / kms_per_radian

    db = DBSCAN(eps=epsilon, min_samples=min_samples, metric='haversine')
    labels = db.fit_predict(coords_rad)

    for item, label in zip(valid_items, labels):
        cid = int(label)
        item["cluster_id"] = cid
        item["is_interdiction_zone"] = (cid >= 0)

    return predictions
