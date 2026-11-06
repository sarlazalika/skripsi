import sqlite3
import json

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row

# 1. Upload sessions
sessions = conn.execute("SELECT * FROM upload_session ORDER BY id DESC").fetchall()
print("=== UPLOAD SESSIONS ===")
for s in sessions:
    print(f"  ID={s['id']} | File={s['filename']} | Total Rows={s['total_rows']} | Status={s['status']} | Waktu={s['upload_time']}")

# 2. Raw data count per session
print("\n=== RAW DATA TEMP (per session) ===")
raw_counts = conn.execute("SELECT session_id, COUNT(*) as cnt FROM raw_data_temp GROUP BY session_id ORDER BY session_id DESC").fetchall()
for r in raw_counts:
    print(f"  session_id={r['session_id']} | raw_rows={r['cnt']}")

# 3. Cleaned transaksi per session
print("\n=== CLEANED TRANSAKSI (per session) ===")
cleaned = conn.execute("SELECT session_id, COUNT(*) as cnt FROM cleaned_transaksi GROUP BY session_id ORDER BY session_id DESC").fetchall()
for c in cleaned:
    print(f"  session_id={c['session_id']} | cleaned_rows={c['cnt']}")

# 4. Cleaning stats
print("\n=== CLEANING STATS ===")
stats = conn.execute("SELECT * FROM cleaning_stats ORDER BY session_id DESC").fetchall()
for st in stats:
    reasons = json.loads(st['cleaning_reasons']) if st['cleaning_reasons'] else []
    print(f"  session_id={st['session_id']} | raw={st['total_raw']} | clean={st['total_clean']} | batal={st['total_batal']} | invalid={st['total_invalid']} | pct_valid={st['pct_valid']}%")
    for r in reasons:
        print(f"    - {r}")

# 5. Active session (yang dipakai analisis)
active = conn.execute("SELECT * FROM upload_session WHERE status='cleaned' ORDER BY id DESC LIMIT 1").fetchone()
print("\n=== ACTIVE SESSION (untuk Dashboard/MA/Apriori) ===")
if active:
    print(f"  ID={active['id']} | File={active['filename']} | Rows={active['total_rows']}")
else:
    print("  Tidak ada active session.")

# 6. Total transaksi table
total_t = conn.execute("SELECT COUNT(*) FROM transaksi").fetchone()[0]
print(f"\n=== TABEL TRANSAKSI (menu Transaksi) ===")
print(f"  Total rows: {total_t}")

# 7. Cek duplikasi: session aktif vs total transaksi
if active:
    cleaned_count = conn.execute("SELECT COUNT(*) FROM cleaned_transaksi WHERE session_id=?", (active['id'],)).fetchone()[0]
    print(f"\n=== CEK POTENSI DOBEL ===")
    print(f"  cleaned_transaksi (session aktif): {cleaned_count}")
    print(f"  tabel transaksi (total semua): {total_t}")
    if total_t > cleaned_count:
        print(f"  --> Ada {total_t - cleaned_count} baris EXTRA di tabel transaksi vs cleaned_transaksi session aktif.")
    else:
        print(f"  --> Tidak ada data extra/dobel terdeteksi.")

conn.close()
