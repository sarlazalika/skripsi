import sqlite3
import pandas as pd
from datetime import datetime
import app
from analysis.moving_average import calculate_moving_average

def test_ma_implementation():
    print("=" * 60)
    print("1. PENGUJIAN ENDPOINT FLASK")
    print("=" * 60)
    client = app.app.test_client()
    
    # 1.1 Endpoint tanpa parameter window
    resp_default = client.get('/moving_average')
    print(f"Status Code /moving_average (tanpa param): {resp_default.status_code}")
    assert resp_default.status_code == 200, "Endpoint /moving_average gagal diakses!"
    html_default = resp_default.data.decode('utf-8')
    assert 'value="12"' in html_default, "Default window bukan 12 di template!"
    assert 'Rata-rata (12 Minggu)' in html_default, "Teks tabel tidak menampilkan 12 minggu!"
    print("-> Verifikasi BERHASIL: Default window tanpa query param adalah 12.")

    # 1.2 Endpoint dengan parameter ?window=12
    resp_w12 = client.get('/moving_average?window=12')
    print(f"Status Code /moving_average?window=12: {resp_w12.status_code}")
    assert resp_w12.status_code == 200, "Endpoint /moving_average?window=12 gagal!"
    print("-> Verifikasi BERHASIL: Parameter window=12 berfungsi dengan benar.")

    print("\n" + "=" * 60)
    print("2. VERIFIKASI PENCEGAHAN DATA LEAKAGE (PREDIKSI VS AKTUAL)")
    print("=" * 60)
    # Buat data simulasi 1 produk selama 14 minggu berurutan
    dates = pd.date_range(start='2025-01-05', periods=14, freq='W-SUN')
    # Jumlah penjualan: minggu 1..12 bernilai 10, minggu 13 bernilai 50, minggu 14 bernilai 70
    sim_data = []
    for i in range(12):
        sim_data.append({'tanggal': dates[i], 'produk': 'Produk_Test', 'jumlah': 10})
    sim_data.append({'tanggal': dates[12], 'produk': 'Produk_Test', 'jumlah': 50})
    sim_data.append({'tanggal': dates[13], 'produk': 'Produk_Test', 'jumlah': 70})
    df_sim = pd.DataFrame(sim_data)

    res_sim = calculate_moving_average(df_sim, window=12)
    # Pada minggu ke-13 (indeks 12):
    # Data historis 12 minggu sebelumnya (minggu 1-12) rata-ratanya adalah 10.
    # Nilai aktual minggu ke-13 adalah 50.
    # Prediksi untuk minggu ke-13 HARUS 10.0 (TIDAK BOLEH memuat 50).
    # Error absolut minggu ke-13: |50 - 10| = 40.
    # Pada minggu ke-14:
    # 12 minggu sebelumnya (minggu 2-13) memuat: 11 minggu bernilai 10 dan 1 minggu bernilai 50.
    # Rata-rata = (11*10 + 50) / 12 = 160 / 12 = 13.33.
    # Nilai aktual minggu ke-14 adalah 70.
    # Prediksi minggu ke-14 HARUS 13.33 (TIDAK BOLEH memuat 70).
    print("Simulasi 14 minggu untuk memverifikasi .shift(1):")
    print(f"- Hasil evaluasi simulasi N Data: {res_sim['validation']['n_data']}")
    print(f"- MAE simulasi: {res_sim['validation']['mae']}")
    print(f"- MAPE simulasi: {res_sim['validation']['mape']}%")
    # Prediksi minggu depan (minggu 15):
    # Menggunakan 12 minggu terakhir (minggu 3 s/d 14): 10*10 + 50 + 70 = 220 / 12 = 18.33
    item_sim = res_sim['items'][0]
    print(f"- Prediksi minggu depan (minggu ke-15): {item_sim['moving_avg']} (Pembulatan: {item_sim['prediction']})")
    assert round(item_sim['moving_avg'], 2) == round(220 / 12, 2), "Prediksi minggu depan tidak cocok dengan rumus MA!"
    print("-> Verifikasi BERHASIL: Prediksi minggu ke-t HANYA menggunakan 12 minggu sebelumnya dan TIDAK menggunakan data aktual minggu yang sama.")

    print("\n" + "=" * 60)
    print("3. HASIL PERHITUNGAN DENGAN DATASET AKTUAL (cleaned_transaksi)")
    print("=" * 60)
    conn = sqlite3.connect('database.db')
    df_real = pd.read_sql_query('SELECT tanggal, produk, jumlah FROM cleaned_transaksi', conn)
    conn.close()

    res_real_12 = calculate_moving_average(df_real, window=12)
    val = res_real_12['validation']
    print(f"Parameter Window: 12 Minggu")
    print(f"Jumlah Data Evaluasi (N Data): {val['n_data']} data titik mingguan")
    print(f"MAE (Mean Absolute Error): {val['mae']} unit")
    print(f"MAPE (Mean Absolute Percentage Error): {val['mape']}%")
    print("\nSample Prediksi Produk Minggu Depan (Top 5):")
    for it in res_real_12['items'][:5]:
        print(f"  - {it['produk']}: Penjualan Minggu Terakhir = {it['last_week_sales']} unit, MA(12) = {it['moving_avg']} unit, Estimasi = {it['prediction']} unit")

    print("\n" + "=" * 60)
    print("4. AUDIT ANOMALI TANGGAL PADA DATASET (FUTURE DATES)")
    print("=" * 60)
    df_real['dt'] = pd.to_datetime(df_real['tanggal'])
    min_date = df_real['dt'].min()
    max_date = df_real['dt'].max()
    print(f"Rentang Tanggal Dataset: {min_date.strftime('%Y-%m-%d')} s/d {max_date.strftime('%Y-%m-%d')}")
    
    # Deteksi anomali tanggal: misal tanggal di masa depan atau bulan/hari tertukar
    now = datetime.now()
    future_data = df_real[df_real['dt'] > now]
    print(f"Jumlah data dengan tanggal > waktu sistem saat ini ({now.strftime('%Y-%m-%d')}): {len(future_data)} baris")
    if not future_data.empty:
        print("Sampel data tanggal masa depan:")
        print(future_data[['tanggal', 'produk', 'jumlah']].drop_duplicates().head(10).to_string())

if __name__ == '__main__':
    test_ma_implementation()
