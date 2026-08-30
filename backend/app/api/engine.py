from fastapi import APIRouter, Request, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
import networkx as nx
import numpy as np
from sklearn.cluster import DBSCAN
from app.db.mongo import get_database

router = APIRouter(prefix="/engine", tags=["Intelligence Engine"])

SEED_NODES = [
    {"_id": "n_victim_1", "type": "VICTIM", "riskScore": 95, "status": "ACTIVE", "metadata": {"name": "Victim Account A"}},
    {"_id": "n_mule_1", "type": "MULE", "riskScore": 20, "status": "ACTIVE", "metadata": {"name": "Mule Account 101"}},
    {"_id": "n_atm_104", "type": "ATM", "riskScore": 10, "status": "ACTIVE", "metadata": {"lat": 16.5062, "lng": 80.6480, "location_id": "ATM-104"}},
    {"_id": "n_atm_221", "type": "ATM", "riskScore": 15, "status": "ACTIVE", "metadata": {"lat": 16.5044, "lng": 80.6558, "location_id": "ATM-221"}},
]

SEED_EDGES = [
    {"source": "n_victim_1", "target": "n_mule_1", "type": "TRANSFER"},
    {"source": "n_mule_1", "target": "n_atm_104", "type": "WITHDRAWAL"},
    {"source": "n_mule_1", "target": "n_atm_221", "type": "WITHDRAWAL"},
]

def get_db(request: Request):
    if hasattr(request.app, "mongodb") and request.app.mongodb is not None:
        return request.app.mongodb
    return get_database()

@router.post("/propagate-risk")
@router.post("/api/engine/propagate-risk")
async def propagate_risk_and_find_hotspots(request: Request):
    db = get_db(request)

    # 1. Fetch all active nodes and edges (seed baseline if empty)
    nodes_count = await db["nodes"].count_documents({"status": {"$ne": "FROZEN"}})
    if nodes_count == 0:
        await db["nodes"].insert_many(SEED_NODES)
        await db["edges"].insert_many(SEED_EDGES)

    nodes = await db["nodes"].find({"status": {"$ne": "FROZEN"}}).to_list(length=200)
    edges = await db["edges"].find().to_list(length=200)

    # 2. Build NetworkX Directed Graph
    G = nx.DiGraph()

    for node in nodes:
        node_id = str(node.get("_id") or node.get("id"))
        G.add_node(
            node_id,
            type=node.get("type"),
            risk_score=float(node.get("riskScore", 0)),
            metadata=node.get("metadata", {})
        )

    for edge in edges:
        src = str(edge.get("source"))
        tgt = str(edge.get("target"))
        if src in G.nodes and tgt in G.nodes:
            G.add_edge(src, tgt, type=edge.get("type"))

    # 3. BFS Risk Propagation Logic starting from Victim nodes
    victim_nodes = [n for n, attr in G.nodes(data=True) if attr["type"] == "VICTIM"]

    for victim in victim_nodes:
        for source, target in nx.bfs_edges(G, source=victim):
            source_risk = G.nodes[source]["risk_score"]
            target_risk = G.nodes[target]["risk_score"]
            
            # Target inherits 95% of source risk score (capped at 99)
            new_risk = max(target_risk, source_risk * 0.95)
            capped_risk = min(99.0, new_risk)
            G.nodes[target]["risk_score"] = capped_risk

            # Update MongoDB document
            if ObjectId.is_valid(target):
                query = {"$or": [{"_id": ObjectId(target)}, {"_id": target}]}
            else:
                query = {"$or": [{"_id": target}, {"id": target}]}

            await db["nodes"].update_one(
                query,
                {"$set": {"riskScore": capped_risk}}
            )

    # 4. Extract High-Risk Terminal Nodes (ATMs)
    high_risk_atms = []
    for n, attr in G.nodes(data=True):
        if attr["type"] == "ATM" and attr["risk_score"] > 70:
            meta = attr.get("metadata", {})
            if "lat" in meta and "lng" in meta:
                high_risk_atms.append({
                    "id": n,
                    "risk_score": round(attr["risk_score"], 2),
                    "lat": meta["lat"],
                    "lng": meta["lng"]
                })

    # 5. Geolocation Clustering with DBSCAN (Haversine metric, Ball Tree)
    interdiction_zones = []
    
    if len(high_risk_atms) > 0:
        coords = np.array([[atm["lat"], atm["lng"]] for atm in high_risk_atms])
        coords_radians = np.radians(coords)
        
        EARTH_RADIUS_KM = 6371.0
        ZONE_RADIUS_KM = 5.0
        epsilon = ZONE_RADIUS_KM / EARTH_RADIUS_KM
        
        dbscan = DBSCAN(eps=epsilon, min_samples=1, metric='haversine', algorithm='ball_tree')
        cluster_labels = dbscan.fit_predict(coords_radians)
        
        clusters: Dict[int, List[Dict[str, Any]]] = {}
        for atm, label in zip(high_risk_atms, cluster_labels):
            cid = int(label)
            if cid not in clusters:
                clusters[cid] = []
            clusters[cid].append(atm)
            
        for label, atms in clusters.items():
            center_lat = sum(a["lat"] for a in atms) / len(atms)
            center_lng = sum(a["lng"] for a in atms) / len(atms)
            
            interdiction_zones.append({
                "zone_id": f"ZONE-{label + 1}",
                "center_coordinates": {"lat": round(center_lat, 6), "lng": round(center_lng, 6)},
                "radius_km": ZONE_RADIUS_KM,
                "targeted_atms": atms,
                "recommended_action": "DISPATCH_UNIT"
            })

    return {
        "status": "success",
        "nodes_scored": len(G.nodes),
        "interdiction_zones": interdiction_zones
    }
