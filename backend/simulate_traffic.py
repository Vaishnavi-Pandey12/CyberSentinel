import os
import sys
import time
import random
from pymongo import MongoClient
from datetime import datetime, timezone

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Connect to MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["cybersentinel"]
nodes_col = db["nodes"]
edges_col = db["edges"]

def simulate_live_fraud():
    print("🚨 INITIATING LIVE TRAFFIC SIMULATION...")
    print("Press CTRL+C to stop the simulation.")
    
    # Grab active accounts to simulate traffic between
    victims = list(nodes_col.find({"type": "VICTIM"}))
    mules = list(nodes_col.find({"type": "MULE"}))
    
    if not victims or not mules:
        # Fallback: if no explicit type filter matches, grab all non-ATM nodes
        all_nodes = list(nodes_col.find({"type": {"$ne": "ATM"}}))
        if len(all_nodes) >= 2:
            victims = all_nodes[:len(all_nodes)//2]
            mules = all_nodes[len(all_nodes)//2:]
        else:
            print("Error: Please run seed_db.py first to populate baseline nodes.")
            return

    try:
        transaction_count = 1
        while True:
            # Pick a random victim and a random mule
            victim = random.choice(victims)
            mule = random.choice(mules)
            
            # Generate a realistic but random transfer amount
            amount = round(random.uniform(5000, 75000), 2)
            
            # Inject the new edge into the database
            edges_col.insert_one({
                "source": victim["_id"],
                "target": mule["_id"],
                "type": "TRANSFER",
                "weight": amount,
                "timestamp": datetime.now(timezone.utc)
            })
            
            victim_name = victim.get("metadata", {}).get("label") or victim.get("label") or str(victim["_id"])
            mule_name = mule.get("metadata", {}).get("label") or mule.get("label") or str(mule["_id"])
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Tx #{transaction_count}: ₹{amount:,.2f} transferred from {victim_name} -> {mule_name}")
            
            transaction_count += 1
            # Wait 3 seconds before the next fraudulent transfer
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n🛑 Simulation terminated.")

if __name__ == "__main__":
    simulate_live_fraud()
