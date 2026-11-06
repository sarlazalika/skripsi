import sys
import sqlite3
import pandas as pd
import app

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row

# Ambil active dataset
active_ds = app.get_active_dataset()
session_ids = app.get_dataset_session_ids(active_ds['id'])
placeholders, params = app.build_session_in_clause(session_ids)

print("Active Dataset:", dict(active_ds))
print("Session IDs in Dataset:", session_ids)

# Query grafik
sales_data = conn.execute(f'''
    SELECT strftime('%Y-%m', tanggal) as bulan, SUM(jumlah) as total
    FROM cleaned_transaksi
    WHERE session_id IN ({placeholders})
    GROUP BY bulan
    ORDER BY bulan DESC
    LIMIT 6
''', params).fetchall()

labels = [row['bulan'] for row in sales_data][::-1]
values = [row['total'] for row in sales_data][::-1]

print("\nData Grafik Dashboard (6 bulan terakhir):")
for l, v in zip(labels, values):
    print(f"  Bulan: {l} | Total Jumlah: {v}")

# Cek seluruh distribusi bulan di cleaned_transaksi
print("\nSeluruh Distribusi Bulan di cleaned_transaksi (sesuai session_ids):")
all_months = conn.execute(f'''
    SELECT strftime('%Y-%m', tanggal) as bulan, count(*) as count_transaksi, SUM(jumlah) as total_qty
    FROM cleaned_transaksi
    WHERE session_id IN ({placeholders})
    GROUP BY bulan
    ORDER BY bulan ASC
''', params).fetchall()
for m in all_months:
    print(f"  Bulan: {m['bulan']} | Transaksi: {m['count_transaksi']} | Qty: {m['total_qty']}")

# Cek rentang tanggal di file sumber (nama file dan tanggal asli raw_data_temp)
print("\nRentang Tanggal di raw_data_temp per Sesi:")
for s_id in session_ids:
    sess_info = conn.execute("SELECT filename FROM upload_session WHERE id=?", (s_id,)).fetchone()
    raw_s = conn.execute("SELECT row_data FROM raw_data_temp WHERE session_id=?", (s_id,)).fetchall()
    dates_in_raw = []
    for r in raw_s:
        import json
        d = json.loads(r['row_data'])
        t = d.get('Waktu Pengiriman Diatur') or d.get('Waktu Pesanan Dibuat') or d.get('Tanggal')
        if t:
            dates_in_raw.append(str(t)[:10])
    if dates_in_raw:
        print(f"  Sesi {s_id} ({sess_info['filename']}):")
        print(f"    Min Asli: {min(dates_in_raw)} | Max Asli: {max(dates_in_raw)} | Total Raw: {len(raw_s)}")

conn.close()
