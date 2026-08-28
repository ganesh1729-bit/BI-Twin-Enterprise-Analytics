import sqlite3
import pandas as pd
import numpy as np
import json
import csv
from datetime import datetime, timedelta

print("Initializing Enterprise Data Generation (Phase 1)...")

# Setup timeline (60 days ending Aug 24, 2026)
days = 60
start_date = datetime(2026, 6, 25)
dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]

transactions = []
marketing_logs = []
supply_chain = []

np.random.seed(42)

for i, date in enumerate(dates):
    # ==========================================
    # SCENARIO 1: Multi-Factor Crash (North)
    # Both Price and Volume drop due to an ad spend cut and competitor discounting.
    # ==========================================
    price_n = 100.0
    vol_n = int(np.random.normal(500, 20))
    ad_spend_n = 5000
    
    if date == '2026-08-21':
        price_n = 80.0  # 20% Price Cut
        vol_n = 300     # 40% Volume Drop
        ad_spend_n = 1000 # Massive marketing drop
        
    transactions.append((date, 'North', 'Standard_Widget', price_n, vol_n, price_n * vol_n))
    marketing_logs.append({"date": date, "region": "North", "metric": "ad_spend", "value": ad_spend_n, "status": "active" if ad_spend_n > 2000 else "budget_paused"})
    supply_chain.append([date, 'North', 'Standard_Widget', 2000]) # Stock is fine

    # ==========================================
    # SCENARIO 2: Sparse History / Cold Start (South)
    # A new product launched just 10 days ago. 14-day rolling stats will fail here.
    # ==========================================
    if i >= 50: # Only generates data for the last 10 days
        price_s = 150.0
        vol_s = int(np.random.normal(200, 15))
        
        # Minor 15% drop on Aug 21 to test sparse threshold
        if date == '2026-08-21':
            vol_s = 170 
            
        transactions.append((date, 'South', 'Premium_Widget', price_s, vol_s, price_s * vol_s))
        marketing_logs.append({"date": date, "region": "South", "metric": "ad_spend", "value": 3000, "status": "launch_campaign"})
        supply_chain.append([date, 'South', 'Premium_Widget', 500])

    # ==========================================
    # SCENARIO 3: Low-Confidence / Abstention (East)
    # Revenue crashes, but all logs and supply chain data look perfectly normal. 
    # AI must refuse to guess.
    # ==========================================
    price_e = 50.0
    vol_e = int(np.random.normal(1000, 50))
    
    if date == '2026-08-21':
        vol_e = 400 # Massive unexplained volume crash
        
    transactions.append((date, 'East', 'Budget_Widget', price_e, vol_e, price_e * vol_e))
    # Logs remain completely normal despite the crash!
    marketing_logs.append({"date": date, "region": "East", "metric": "ad_spend", "value": 4000, "status": "active"})
    supply_chain.append([date, 'East', 'Budget_Widget', 5000])


# --- SAVE SOURCE 1: SQLite (Structured Transactions) ---
conn = sqlite3.connect('enterprise_data.db')
cursor = conn.cursor()
cursor.execute('DROP TABLE IF EXISTS sales')
cursor.execute('''CREATE TABLE sales (date TEXT, region TEXT, product TEXT, price REAL, volume INTEGER, revenue REAL)''')
cursor.executemany('INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?)', transactions)
conn.commit()
conn.close()
print("✓ Created Source 1: enterprise_data.db (SQL)")

# --- SAVE SOURCE 2: JSON (Unstructured Marketing Telemetry) ---
with open('marketing_telemetry.json', 'w') as f:
    json.dump(marketing_logs, f, indent=4)
print("✓ Created Source 2: marketing_telemetry.json (JSON)")

# --- SAVE SOURCE 3: CSV (Supply Chain Manifests) ---
with open('supply_chain_manifest.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['date', 'region', 'product', 'inventory_level'])
    writer.writerows(supply_chain)
print("✓ Created Source 3: supply_chain_manifest.csv (CSV)")

print("\nPhase 1 Complete! Data matrix successfully generated.")