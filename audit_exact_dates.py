import sqlite3
import pandas as pd
import datetime
import random

def run_audit():
    conn = sqlite3.connect('database.db')
    
    # Get active session
    session = pd.read_sql_query("SELECT id FROM upload_session WHERE status='cleaned' ORDER BY id DESC LIMIT 1", conn)
    if session.empty:
        session_id = pd.read_sql_query("SELECT id FROM upload_session ORDER BY id DESC LIMIT 1", conn).iloc[0]['id']
    else:
        session_id = session.iloc[0]['id']
        
    df = pd.read_sql_query('SELECT tanggal, produk, jumlah FROM cleaned_transaksi WHERE session_id=?', conn, params=(int(session_id),))
    conn.close()
    
    df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce')
    df = df.dropna(subset=['tanggal'])
    
    global_min = df['tanggal'].min()
    global_max = df['tanggal'].max()
    
    print(f"1. Global Min Date: {global_min.strftime('%Y-%m-%d')}")
    print(f"1. Global Max Date: {global_max.strftime('%Y-%m-%d')}")
    
    # Check future dates (relative to 2026-09-22)
    today = pd.to_datetime('2026-09-22')
    future_df = df[df['tanggal'] > today]
    print(f"\n2. Future Dates count: {len(future_df)}")
    if not future_df.empty:
        print(future_df['tanggal'].dt.strftime('%Y-%m-%d').value_counts())
        
    unique_products = df['produk'].nunique()
    print(f"\n3. Total Unique Products: {unique_products}")
    
    # Total expected weeks
    global_idx = pd.date_range(start=global_min, end=global_max, freq='W-SUN')
    expected_weeks_total = len(global_idx)
    print(f"\n4. Total Calendar Weeks (Min to Max): {expected_weeks_total}")
    
    # 5. Pick 5 random products
    print("\n5. 5 Random Products Audit:")
    products = list(df['produk'].unique())
    random.seed(42) # For reproducibility
    sample_products = random.sample(products, min(5, len(products)))
    
    weekly_sales = df.set_index('tanggal').groupby('produk')['jumlah'].resample('W').sum().reset_index()
    
    for p in sample_products:
        p_data = df[df['produk'] == p]
        p_min = p_data['tanggal'].min()
        p_max = p_data['tanggal'].max()
        current_resample = weekly_sales[weekly_sales['produk'] == p]
        current_weeks = len(current_resample)
        
        # Check missing weeks
        p_idx = pd.date_range(start=global_min, end=global_max, freq='W-SUN')
        
        print(f"\nProduct: {p}")
        print(f"  First Trans: {p_min.strftime('%Y-%m-%d')}")
        print(f"  Last Trans: {p_max.strftime('%Y-%m-%d')}")
        print(f"  Current Weeks: {current_weeks}")
        print(f"  Expected Weeks: {expected_weeks_total}")
        
        # Example of a missing week
        current_dates = set(current_resample['tanggal'])
        all_dates = set(p_idx)
        missing = all_dates - current_dates
        if missing:
            example = sorted(list(missing))[len(missing)//2] # middle missing week
            print(f"  Example missing week: {example.strftime('%Y-%m-%d')}")
        else:
            print("  No missing weeks")

if __name__ == "__main__":
    run_audit()
