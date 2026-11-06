import sqlite3
import pandas as pd
import json

conn = sqlite3.connect('database.db')

# Get session info
session = pd.read_sql_query('SELECT * FROM upload_session ORDER BY id DESC LIMIT 1', conn)
if not session.empty:
    print("=== SESSION INFO ===")
    print(session.iloc[0].to_dict())
    
# Check raw data
raw = pd.read_sql_query('SELECT * FROM raw_data_temp', conn)
print(f"\n=== RAW DATA COUNT: {len(raw)} ===")

# Parse raw JSON
raw_parsed = []
for _, r in raw.iterrows():
    raw_parsed.append(json.loads(r['row_data']))
df_raw = pd.DataFrame(raw_parsed)

print("Raw Columns:", df_raw.columns.tolist())

# Check cleaned data
clean = pd.read_sql_query('SELECT * FROM cleaned_transaksi', conn)
print(f"\n=== CLEANED DATA COUNT: {len(clean)} ===")

# Check cleaning stats
stats = pd.read_sql_query('SELECT * FROM cleaning_stats', conn)
if not stats.empty:
    print("\n=== CLEANING STATS ===")
    print(stats.iloc[0].to_dict())

# Let's see some statuses in raw
mapping = json.loads(session.iloc[0]['column_mapping'])
status_col = mapping.get('status')
if status_col and status_col in df_raw.columns:
    print(f"\n=== RAW STATUS DISTRIBUTION (Column: {status_col}) ===")
    print(df_raw[status_col].value_counts())
    
# Check if any cancelled made it to cleaned
# (We need to join id_transaksi to see)
id_col = mapping.get('id_transaksi')
if id_col and status_col:
    # Get ids of cancelled
    cancelled_ids = df_raw[df_raw[status_col].astype(str).str.lower().str.contains('batal')][id_col].astype(str).str.strip().tolist()
    in_clean = clean[clean['id_transaksi'].isin(cancelled_ids)]
    print(f"\n=== CANCELLED IN CLEANED: {len(in_clean)} ===")

# Check missing values in clean
print("\n=== MISSING VALUES IN CLEANED ===")
print(clean.isnull().sum())

# Check duplicates
print(f"\n=== DUPLICATES IN CLEANED: {clean.duplicated(subset=['id_transaksi', 'produk']).sum()} ===")

# Date format in clean
print("\n=== CLEANED DATE SAMPLE ===")
print(clean['tanggal'].head())

conn.close()
