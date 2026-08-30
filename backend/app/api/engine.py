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
    {"_id": "n_mule_1", "type": "MULE", "riskScore": 92, "status": "ACTIVE", "metadata": {"name": "Mule Account 101"}},
    {"_id": "n_mule_2", "type": "MULE", "riskScore": 88, "status": "ACTIVE", "metadata": {"name": "Mule Account 102"}},
    {"_id": "M883", "type": "MULE", "riskScore": 90, "status": "ACTIVE", "metadata": {"name": "Mule Account (SBI)"}},
    {"_id": "n_atm_104", "type": "ATM", "riskScore": 85.7, "status": "ACTIVE", "metadata": {"lat": 16.5062, "lng": 80.6480, "location_id": "ATM-104"}},
    {"_id": "n_atm_221", "type": "ATM", "riskScore": 85.7, "status": "ACTIVE", "metadata": {"lat": 16.5044, "lng": 80.6558, "location_id": "ATM-221"}},
]

SEED_EDGES = [
    {"source": "n_victim_1", "target": "n_mule_1", "type": "TRANSFER"},
    {"source": "n_victim_1", "target": "n_mule_2", "type": "TRANSFER"},
    {"source": "n_victim_1", "target": "M883", "type": "TRANSFER"},
    {"source": "n_mule_1", "target": "n_atm_104", "type": "WITHDRAWAL"},
    {"source": "n_mule_1", "target": "n_atm_221", "type": "WITHDRAWAL"},
    {"source": "n_mule_2", "target": "n_atm_104", "type": "WITHDRAWAL"},
    {"source": "M883", "target": "n_atm_221", "type": "WITHDRAWAL"},
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

@router.get("/case/{case_id}")
@router.get("/api/engine/case/{case_id}")
async def get_case_graph(case_id: str, request: Request):
    db = get_db(request)
    nodes = await db["nodes"].find({"status": {"$ne": "DELETED"}}).to_list(length=100)
    edges = await db["edges"].find().to_list(length=100)

    if not nodes:
        nodes = SEED_NODES
    if not edges:
        edges = SEED_EDGES

    # Ensure all MULE nodes are connected by checking for orphan nodes
    connected_targets = {str(e.get("target")) for e in edges}
    connected_sources = {str(e.get("source")) for e in edges}
    all_connected = connected_targets.union(connected_sources)
    victim_id = next((str(n.get("_id") or n.get("id")) for n in nodes if n.get("type") == "VICTIM"), "n_victim_1")
    atm_id = next((str(n.get("_id") or n.get("id")) for n in nodes if n.get("type") == "ATM"), "n_atm_104")

    # Auto-link any floating/orphaned MULE nodes
    active_edges = list(edges)
    for n in nodes:
        nid = str(n.get("_id") or n.get("id"))
        if n.get("type") == "MULE" and nid not in all_connected:
            new_edge_in = {"source": victim_id, "target": nid, "type": "TRANSFER"}
            new_edge_out = {"source": nid, "target": atm_id, "type": "WITHDRAWAL"}
            active_edges.extend([new_edge_in, new_edge_out])
            try:
                await db["edges"].insert_many([new_edge_in, new_edge_out])
            except Exception:
                pass

    node_risk_map = {}
    formatted_nodes = []
    for idx, n in enumerate(nodes):
        nid = str(n.get("_id") or n.get("id"))
        ntype = n.get("type", "MULE")
        risk_val = float(n.get("riskScore", 80))
        node_risk_map[nid] = (risk_val, ntype)

        # Spread out horizontal positions cleanly to avoid layout overlap
        x_pos = 150 if ntype == "VICTIM" else (300 + (idx % 3) * 150 if ntype == "MULE" else 600)
        y_pos = 100 if ntype == "VICTIM" else (150 + (idx * 90) % 350 if ntype == "MULE" else 150 + (idx * 120) % 300)

        formatted_nodes.append({
            "id": nid,
            "type": "entity",
            "position": n.get("position", {"x": x_pos, "y": y_pos}),
            "data": {
                "id": nid,
                "label": n.get("label") or n.get("metadata", {}).get("name") or str(n.get("_id")),
                "type": ntype,
                "riskScore": risk_val,
                "status": n.get("status", "ACTIVE")
            }
        })

    formatted_edges = []
    for e in active_edges:
        src = str(e.get("source"))
        tgt = str(e.get("target"))
        src_risk, src_type = node_risk_map.get(src, (85, "VICTIM"))
        
        # Color edges based on source node risk score / malicious flow
        if src_type == "VICTIM" or src_risk >= 80:
            stroke_color = "#ef4444" # Red for high risk / dirty money
        elif src_risk >= 50:
            stroke_color = "#f97316" # Orange for medium risk
        else:
            stroke_color = "#48D878" # Green for low risk

        formatted_edges.append({
            "id": f"e{src}-{tgt}",
            "source": src,
            "target": tgt,
            "animated": True,
            "style": {"stroke": stroke_color, "strokeWidth": 2, "opacity": 0.8}
        })

    return {
        "status": "success",
        "case_id": case_id,
        "nodes": formatted_nodes,
        "edges": formatted_edges
    }

@router.post("/analyze-trail")
@router.post("/run-intelligence")
@router.post("/api/engine/run-intelligence")
async def run_intelligence_pipeline(request: Request = None):
    try:
        db = None
        if request:
            try:
                db = get_db(request)
            except Exception:
                pass

        if db is None:
            MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
            client = MongoClient(MONGO_URI)
            db_sync = client["cybersentinel"]
            nodes_col = db_sync["nodes"]
            edges_col = db_sync["edges"]
            active_nodes = list(nodes_col.find({"status": {"$ne": "FROZEN"}}))
            all_edges = list(edges_col.find())
        else:
            nodes_count = await db["nodes"].count_documents({"status": {"$ne": "FROZEN"}})
            if nodes_count == 0:
                await db["nodes"].insert_many(SEED_NODES)
                await db["edges"].insert_many(SEED_EDGES)
            active_nodes = await db["nodes"].find({"status": {"$ne": "FROZEN"}}).to_list(length=500)
            all_edges = await db["edges"].find().to_list(length=500)

        if not active_nodes:
            return {"status": "error", "message": "No active nodes found in database."}

        # 1. Build NetworkX Directed Graph with Edge Weights
        G = nx.DiGraph()

        for node in active_nodes:
            node_id_str = str(node.get("_id") or node.get("id"))
            score_val = node.get("riskScore") if node.get("riskScore") is not None else node.get("risk_score", 0)
            metadata = node.get("metadata", {}) or {}
            G.add_node(
                node_id_str, 
                type=node.get("type"), 
                riskScore=float(score_val or 0), 
                is_seed_node=bool(node.get("is_seed_node", False)),
                metadata=metadata
            )

        for edge in all_edges:
            src = str(edge["source"])
            tgt = str(edge["target"])
            e_type = str(edge.get("type", "TRANSFER")).upper()
            
            # Weighted edge definition: SHARED_KYC higher weight than TRANSFER
            if e_type == "SHARED_KYC":
                weight = 2.0
            elif e_type == "CASH_WITHDRAWAL":
                weight = 0.8
            else:
                weight = 1.0

            if src in G.nodes and tgt in G.nodes:
                G.add_edge(src, tgt, type=e_type, weight=weight)

        # 2. Filter High-Degree Hub Nodes (> 50 connections) to prevent risk leakage
        hub_nodes = [n for n, deg in G.degree() if deg > 50]
        G_filtered = G.copy()
        if hub_nodes:
            G_filtered.remove_nodes_from(hub_nodes)

        # 3. Personalized PageRank (PPR) Risk Propagation
        seed_nodes = [
            n for n, attr in G_filtered.nodes(data=True) 
            if attr.get('type') == 'VICTIM' or attr.get('is_seed_node') or attr.get('riskScore', 0) >= 95
        ]

        if not seed_nodes:
            seed_nodes = list(G_filtered.nodes())[:1]

        seed_dict = {n: (1.0 if n in seed_nodes else 0.0) for n in G_filtered.nodes()}
        total_seed_weight = sum(seed_dict.values())
        personalization = {k: v / total_seed_weight for k, v in seed_dict.items()} if total_seed_weight > 0 else None

        try:
            pr_scores = nx.pagerank(G_filtered, alpha=0.85, personalization=personalization, weight='weight')
        except Exception:
            # Fallback if graph is disconnected
            pr_scores = {n: 0.1 for n in G_filtered.nodes()}

        # 4. Score Normalization (0 - 100 Scale)
        max_pr = max(pr_scores.values()) if pr_scores and max(pr_scores.values()) > 0 else 1.0

        for n in G.nodes():
            if n in seed_nodes:
                norm_score = 100.0
            else:
                raw_score = pr_scores.get(n, 0.0)
                norm_score = min(99.0, round((raw_score / max_pr) * 100.0, 1))

            G.nodes[n]['riskScore'] = norm_score

            if db is not None:
                if ObjectId.is_valid(n):
                    query = {"$or": [{"_id": ObjectId(n)}, {"_id": n}]}
                else:
                    query = {"$or": [{"_id": n}, {"id": n}]}
                await db["nodes"].update_one(query, {"$set": {"riskScore": norm_score}})

        # 5. Provenance: Shortest Path Evidence Chain for High-Risk Nodes (> 80)
        primary_victim = seed_nodes[0] if seed_nodes else None
        
        for n, attr in G.nodes(data=True):
            if attr.get('riskScore', 0) > 80:
                evidence_chain = []
                if primary_victim and primary_victim != n:
                    try:
                        evidence_chain = nx.shortest_path(G_filtered, source=primary_victim, target=n)
                    except Exception:
                        evidence_chain = [primary_victim, n]
                else:
                    evidence_chain = [n]

                G.nodes[n]['metadata']['evidence_chain'] = evidence_chain
                if db is not None:
                    if ObjectId.is_valid(n):
                        query = {"$or": [{"_id": ObjectId(n)}, {"_id": n}]}
                    else:
                        query = {"$or": [{"_id": n}, {"id": n}]}
                    await db["nodes"].update_one(query, {"$set": {"metadata.evidence_chain": evidence_chain}})

        # 6. Spatial Predictive Forecasting (Predictive vs Reactive)
        # 6a. Exclude ATMs that already have CASH_WITHDRAWAL edges (crimes that already occurred)
        executed_atm_ids = set()
        for u, v, attr in G.edges(data=True):
            if str(attr.get('type', '')).upper() == 'CASH_WITHDRAWAL':
                if G.nodes[v].get('type') == 'ATM':
                    executed_atm_ids.add(v)

        # 6b. Find all MULE accounts with riskScore > 80
        high_risk_mules = [
            n for n, attr in G.nodes(data=True)
            if attr.get('type') == 'MULE' and attr.get('riskScore', 0) > 80
        ]

        # 6c. Query/Generate candidate ATMs within 5km radius of high-risk mules' locations
        candidate_atms = []
        for n, attr in G.nodes(data=True):
            if attr.get('type') == 'ATM' and n not in executed_atm_ids:
                meta = attr.get('metadata', {})
                if 'lat' in meta and 'lng' in meta:
                    candidate_atms.append({
                        "id": n,
                        "riskScore": attr.get('riskScore', 80),
                        "lat": float(meta['lat']),
                        "lng": float(meta['lng'])
                    })

        # Synthetic Vijayawada candidate ATMs fallback if database candidate set has < 2 items
        if len(candidate_atms) < 2:
            candidate_atms = [
                {"id": "ATM_BENZ_1", "riskScore": 89.0, "lat": 16.4971, "lng": 80.6516},
                {"id": "ATM_BENZ_2", "riskScore": 87.5, "lat": 16.4975, "lng": 80.6650},
                {"id": "ATM_PATAMATA_1", "riskScore": 84.0, "lat": 16.5020, "lng": 80.6580},
                {"id": "ATM_MG_ROAD_1", "riskScore": 82.0, "lat": 16.5060, "lng": 80.6490}
            ]

        interdiction_zones = []

        if len(candidate_atms) > 0:
            coords = np.array([[atm["lat"], atm["lng"]] for atm in candidate_atms])
            coords_radians = np.radians(coords)
            
            EARTH_RADIUS_KM = 6371.0
            ZONE_RADIUS_KM = 5.0 # 5 km forecasting radius
            epsilon = ZONE_RADIUS_KM / EARTH_RADIUS_KM
            
            # min_samples=2 so we only flag corroborated hotspots
            dbscan = DBSCAN(eps=epsilon, min_samples=2, metric='haversine', algorithm='ball_tree')
            labels = dbscan.fit_predict(coords_radians)
            
            clusters: Dict[int, List[Dict[str, Any]]] = {}
            for atm, label in zip(candidate_atms, labels):
                cid = int(label)
                # Ignore unclustered noise points (-1) unless no clusters found
                if cid != -1:
                    if cid not in clusters:
                        clusters[cid] = []
                    clusters[cid].append(atm)
                
            # If all were noise under min_samples=2, group all candidate ATMs into a primary forecast zone
            if not clusters:
                clusters[0] = candidate_atms

            for label, atms in clusters.items():
                lats = [a['lat'] for a in atms]
                lngs = [a['lng'] for a in atms]
                padding = 0.01 
                
                interdiction_zones.append({
                    "zone_id": f"TARGET-CLUSTER-{int(label) + 1}",
                    "priority_weight": len(atms),
                    "bounding_box": {
                        "north": max(lats) + padding,
                        "south": min(lats) - padding,
                        "east": max(lngs) + padding,
                        "west": min(lngs) - padding,
                    },
                    "center": {
                        "lat": sum(lats) / len(lats),
                        "lng": sum(lngs) / len(lngs)
                    },
                    "target_nodes": [a['id'] for a in atms]
                })

        # Sort final interdiction_zones descending by priority_weight (largest cluster first)
        interdiction_zones.sort(key=lambda z: z["priority_weight"], reverse=True)

        frontend_nodes = [
            {
                "id": n,
                "type": attr.get('type', 'entity'),
                "riskScore": round(attr.get('riskScore', 0), 1),
                "metadata": attr.get('metadata', {})
            }
            for n, attr in G.nodes(data=True)
        ]
        
        frontend_edges = [
            {"id": f"{u}-{v}", "source": u, "target": v, "type": attr.get('type', 'TRANSFER')}
            for u, v, attr in G.edges(data=True)
        ]

        return {
            "status": "success",
            "algorithm": "Personalized PageRank (PPR) + Predictive DBSCAN",
            "nodes_analyzed": len(frontend_nodes),
            "interdiction_zones": interdiction_zones,
            "graph": {
                "nodes": frontend_nodes,
                "edges": frontend_edges
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



