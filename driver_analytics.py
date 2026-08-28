import sqlite3
import pandas as pd
import json
import warnings

warnings.filterwarnings('ignore')

# 1. Load the Semantic Contract
print("Loading Phase 2 Semantic Contract...")
with open('semantic_contract.json', 'r') as f:
    contract = json.load(f)

cfg = contract['kpis']['revenue']
sigma_limit = cfg['mature_threshold_sigma']
sparse_limit = cfg['sparse_threshold_percent']
sparse_days = cfg['sparse_definition_days']

# 2. Ingest the Data
print("Ingesting structured data from SQLite...")
conn = sqlite3.connect('enterprise_data.db')
df = pd.read_sql_query("SELECT * FROM sales", conn)
conn.close()

df['date'] = pd.to_datetime(df['date'])
df = df.sort_values(by=['region', 'date'])

# 3. Deterministic PVM Engine (Clean Group Processing)
print("Running Deterministic PVM Engine...\n")

processed_groups = []

for region, group in df.groupby('region'):
    group = group.copy()
    
    # 14-day rolling baseline shifted by 1 so today's crash doesn't distort the baseline
    group['base_price'] = group['price'].rolling(14, min_periods=1).mean().shift(1)
    group['base_vol'] = group['volume'].rolling(14, min_periods=1).mean().shift(1)
    group['base_rev'] = group['revenue'].rolling(14, min_periods=1).mean().shift(1)
    group['rev_std'] = group['revenue'].rolling(14, min_periods=1).std().shift(1).fillna(0)
    
    # Track days of history for sparse vs mature logic
    group['history_days'] = range(1, len(group) + 1)
    group['is_mature'] = group['history_days'] >= sparse_days
    
    # Fill first row shifts to prevent NaN comparisons
    group['base_rev'] = group['base_rev'].fillna(group['revenue'])
    group['base_price'] = group['base_price'].fillna(group['price'])
    group['base_vol'] = group['base_vol'].fillna(group['volume'])
    
    # Mathematical Triggers
    group['mature_anomaly'] = group['is_mature'] & (group['revenue'] < (group['base_rev'] - (sigma_limit * group['rev_std'])))
    group['sparse_anomaly'] = (~group['is_mature']) & (group['revenue'] < (group['base_rev'] * (1 - sparse_limit)))
    group['is_anomaly'] = group['mature_anomaly'] | group['sparse_anomaly']
    
    # Price-Volume-Mix Decomposition
    group['price_effect'] = (group['price'] - group['base_price']) * group['volume']
    group['volume_effect'] = (group['volume'] - group['base_vol']) * group['base_price']
    
    processed_groups.append(group)

df = pd.concat(processed_groups, ignore_index=True)

# 4. Output the Findings
anomalies = df[df['is_anomaly'] == True]

for _, row in anomalies.iterrows():
    print(f"🚨 ANOMALY TRIGGERED: {row['region']} Region | Product: {row['product']}")
    print(f"Date: {row['date'].strftime('%Y-%m-%d')}")
    print(f"Rule Applied: {'Mature 2-Sigma Threshold' if row['is_mature'] else 'Sparse History 10% Threshold'}")
    print(f"Revenue Drop: Expected ~${row['base_rev']:,.2f} | Actual ${row['revenue']:,.2f}")
    
    print("--- PVM DECOMPOSITION (Strict Math) ---")
    if row['price_effect'] < -100:
        print(f"📉 Price Driver: ${row['price_effect']:,.2f} (Loss driven by discounting/pricing)")
    if row['volume_effect'] < -100:
        print(f"📉 Volume Driver: ${row['volume_effect']:,.2f} (Loss driven by missing traffic/supply)")
    print("==================================================\n")