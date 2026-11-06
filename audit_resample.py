import sqlite3
import pandas as pd

def run_audit():
    conn = sqlite3.connect('database.db')
    session = pd.read_sql_query("SELECT id FROM upload_session WHERE status='cleaned' ORDER BY id DESC LIMIT 1", conn)
    if session.empty:
        session_id = pd.read_sql_query("SELECT id FROM upload_session ORDER BY id DESC LIMIT 1", conn).iloc[0]['id']
    else:
        session_id = session.iloc[0]['id']
        
    df = pd.read_sql_query('SELECT tanggal, produk, jumlah FROM cleaned_transaksi WHERE session_id=?', conn, params=(int(session_id),))
    conn.close()
    
    df['tanggal'] = pd.to_datetime(df['tanggal'])
    global_min = df['tanggal'].min()
    global_max = df['tanggal'].max()
    print(f"Global Date Range: {global_min} to {global_max}")
    
    # 2. Resample currently
    weekly_sales = df.set_index('tanggal').groupby('produk')['jumlah'].resample('W').sum().reset_index()
    
    # Find 3 interesting products
    # We want products whose max date is significantly less than global_max
    stats = weekly_sales.groupby('produk')['tanggal'].agg(['min', 'max', 'count']).reset_index()
    stats['gap_to_max'] = (global_max - stats['max']).dt.days
    
    interesting = stats.sort_values('gap_to_max', ascending=False).head(3)
    
    print("\n--- SAMPLE PRODUCTS ---")
    for _, row in interesting.iterrows():
        prod = row['produk']
        print(f"\nProduct: {prod}")
        # Current behavior
        current = weekly_sales[weekly_sales['produk'] == prod]
        print("Current Series (dates & qty):")
        for _, r in current.iterrows():
            print(f"  {r['tanggal'].strftime('%Y-%m-%d')} : {r['jumlah']}")
        
        # Expected behavior
        idx = pd.date_range(start=global_min, end=global_max, freq='W-SUN')
        expected = df[df['produk'] == prod].set_index('tanggal')['jumlah'].resample('W').sum().reindex(idx, fill_value=0)
        print("Expected Series (dates & qty):")
        for date, qty in expected.items():
            print(f"  {date.strftime('%Y-%m-%d')} : {qty}")

if __name__ == "__main__":
    run_audit()
