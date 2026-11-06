import sqlite3
import pandas as pd
import random
from analysis.moving_average import calculate_moving_average as calc_after

def calc_before(df, window=3):
    if df.empty: return None
    df = df.copy()
    df['tanggal'] = pd.to_datetime(df['tanggal'])
    weekly_sales = df.set_index('tanggal').groupby('produk')['jumlah'].resample('W').sum().reset_index()
    results = []
    for produk in weekly_sales['produk'].unique():
        prod_data = weekly_sales[weekly_sales['produk'] == produk].copy()
        prod_data = prod_data.sort_values('tanggal')
        prod_data['moving_avg'] = prod_data['jumlah'].rolling(window=window).mean()
        last_row = prod_data.iloc[-1]
        moving_avg_val = last_row['moving_avg']
        if pd.isna(moving_avg_val): moving_avg_val = prod_data['jumlah'].mean()
        results.append({
            'produk': produk,
            'last_week_sales': int(last_row['jumlah']),
            'moving_avg': round(moving_avg_val, 2) if not pd.isna(moving_avg_val) else 0,
            'prediction': round(moving_avg_val, 0) if not pd.isna(moving_avg_val) else 0
        })
    return results

def run_audit():
    conn = sqlite3.connect('database.db')
    session = pd.read_sql_query("SELECT id FROM upload_session WHERE status='cleaned' ORDER BY id DESC LIMIT 1", conn)
    if session.empty:
        session_id = pd.read_sql_query("SELECT id FROM upload_session ORDER BY id DESC LIMIT 1", conn).iloc[0]['id']
    else:
        session_id = session.iloc[0]['id']
        
    df = pd.read_sql_query('SELECT tanggal, produk, jumlah FROM cleaned_transaksi WHERE session_id=?', conn, params=(int(session_id),))
    conn.close()
    
    global_min = pd.to_datetime(df['tanggal']).min()
    global_max = pd.to_datetime(df['tanggal']).max()
    global_idx = pd.date_range(start=global_min, end=global_max, freq='W-SUN')
    expected_weeks = len(global_idx)
    unique_products = df['produk'].nunique()
    
    print(f"1. Jumlah produk unik: {unique_products}")
    print(f"2. Tanggal global min/max: {global_min.strftime('%Y-%m-%d')} hingga {global_max.strftime('%Y-%m-%d')}")
    print(f"3. Jumlah periode mingguan digunakan: {expected_weeks} minggu")
    
    # Check rows per product after fix
    print("\n4. Jumlah baris mingguan setiap produk:")
    for produk in df['produk'].unique():
        prod_data_raw = df[df['produk'] == produk].copy()
        prod_data_raw['tanggal'] = pd.to_datetime(prod_data_raw['tanggal'])
        prod_weekly = prod_data_raw.set_index('tanggal')['jumlah'].resample('W').sum()
        prod_weekly = prod_weekly.reindex(global_idx, fill_value=0).reset_index()
        print(f"  - {produk}: {len(prod_weekly)} baris")
        
    # Sample 5 products
    random.seed(42)
    sample_prods = random.sample(list(df['produk'].unique()), min(5, unique_products))
    print("\n5. Detail 5 Contoh Produk (Menampilkan minggu dengan nilai 0):")
    for p in sample_prods:
        print(f"\nProduk: {p}")
        prod_data_raw = df[df['produk'] == p].copy()
        prod_data_raw['tanggal'] = pd.to_datetime(prod_data_raw['tanggal'])
        prod_weekly = prod_data_raw.set_index('tanggal')['jumlah'].resample('W').sum()
        prod_weekly = prod_weekly.reindex(global_idx, fill_value=0).reset_index()
        prod_weekly.columns = ['tanggal', 'jumlah']
        # find some zero weeks
        zeros = prod_weekly[prod_weekly['jumlah'] == 0]
        if not zeros.empty:
            print(f"  Contoh minggu yg diisi 0: {zeros['tanggal'].iloc[0].strftime('%Y-%m-%d')} (Jumlah: 0)")
        else:
            print(f"  Tidak ada minggu kosong.")
            
    # MA Before vs After (Window = 12)
    res_before = calc_before(df, window=12)
    res_after = calc_after(df, window=12)
    
    before_dict = {x['produk']: x for x in res_before}
    
    print("\n6. Perbandingan Prediksi MA (Window=12):")
    for a in res_after:
        if a['produk'] in sample_prods:
            b = before_dict[a['produk']]
            print(f"\nProduk: {a['produk']}")
            print(f"  SEBELUM -> Last Sales: {b['last_week_sales']} | Prediction: {b['prediction']} | MA: {b['moving_avg']}")
            print(f"  SESUDAH -> Last Sales: {a['last_week_sales']} | Prediction: {a['prediction']} | MA: {a['moving_avg']}")

if __name__ == "__main__":
    run_audit()
