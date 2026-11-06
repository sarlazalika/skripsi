import sys
import io
import sqlite3
import pandas as pd
import app
from analysis.preprocessor import clean_data, detect_column_mapping

sys.stdout.reconfigure(encoding='utf-8')

print("="*60)
print("PENGUJIAN PROSES UPLOAD DAN PREPROCESSING")
print("="*60)

# 1. Buat data sampel pengujian yang mereplikasi format file e-commerce Shopee
csv_content = """No. Pesanan,Waktu Pengiriman Diatur,Nama Produk,Jumlah,Status Pesanan
TEST001,2026-02-11 18:09,Kain Background Foto Studio Kain Polos,2,Selesai
TEST002,2026-02-12 15:07,Kain Background Foto Studio Kain Polos,1,Selesai
TEST003,2026-03-11 15:46,Kain Background Foto Studio Backdrop Blacu,3,Selesai
TEST004,2026-03-12 15:39,Kain Background Foto Studio Backdrop Blacu,2,Selesai
TEST005,2025-11-01 10:15,Kain meteran motif kotak kotak,5,Selesai
TEST006,2026-02-11 19:00,Klip Backdrop Penjepit Kain,4,Selesai
TEST007,2026-02-11 20:00,Kain Background Foto Studio Kain Polos,1,Batal
"""

df_sample = pd.read_csv(io.StringIO(csv_content))
print(f"Data sampel input: {len(df_sample)} baris")

# 2. Uji mapping otomatis
mapping = detect_column_mapping(df_sample)
print("Mapping otomatis:", mapping)
assert mapping['id_transaksi'] == 'No. Pesanan'
assert mapping['tanggal'] == 'Waktu Pengiriman Diatur'
assert mapping['produk'] == 'Nama Produk'
assert mapping['jumlah'] == 'Jumlah'
assert mapping['status'] == 'Status Pesanan'

# 3. Uji clean_data
df_cleaned, stats = clean_data(df_sample, mapping)
print(f"Hasil clean_data: {len(df_cleaned)} baris valid dari {stats['total_raw']} raw")
print(f"Batal: {stats['total_batal']} | Non-item/Invalid: {stats['total_invalid']}")

# Verifikasi tanggal hasil parsing
print("\nHasil Tanggal Cleaned:")
for _, r in df_cleaned.iterrows():
    print(f"  {r['id_transaksi']} | {r['tanggal']} | {r['produk']} | {r['jumlah']} unit")

expected_dates = {
    'TEST001': '2026-02-11',
    'TEST002': '2026-02-12',
    'TEST003': '2026-03-11',
    'TEST004': '2026-03-12',
    'TEST005': '2025-11-01',
}

for order_id, exp_tgl in expected_dates.items():
    actual_tgl = df_cleaned[df_cleaned['id_transaksi'] == order_id]['tanggal'].values[0]
    assert actual_tgl == exp_tgl, f"Gagal! {order_id} tanggal {actual_tgl} != {exp_tgl}"

# Pastikan TEST006 (Klip Backdrop) dibuang sebagai non-item
assert 'TEST006' not in df_cleaned['id_transaksi'].values, "Klip backdrop tidak terfilter!"

# Pastikan TEST007 (Batal) dibuang
assert 'TEST007' not in df_cleaned['id_transaksi'].values, "Status batal tidak terfilter!"

print("\n-> VERIFIKASI PENGUJIAN UPLOAD & PREPROCESSING: SUKSES 100%!")
print("   Tanggal diparsing akurat tanpa inversi hari-bulan, aturan filter non-item & batal tetap terjaga.")
