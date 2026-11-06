import sqlite3
import pandas as pd
from analysis.moving_average import calculate_moving_average

def run_audit():
    conn = sqlite3.connect('database.db')
    session = pd.read_sql_query("SELECT id FROM upload_session WHERE status='cleaned' ORDER BY id DESC LIMIT 1", conn)
    session_id = session.iloc[0]['id'] if not session.empty else pd.read_sql_query("SELECT id FROM upload_session ORDER BY id DESC LIMIT 1", conn).iloc[0]['id']
    df = pd.read_sql_query('SELECT tanggal, produk, jumlah FROM cleaned_transaksi WHERE session_id=?', conn, params=(int(session_id),))
    conn.close()
    
    df['tanggal'] = pd.to_datetime(df['tanggal'])
    global_min = df['tanggal'].min()
    global_max = df['tanggal'].max()
    global_idx = pd.date_range(start=global_min, end=global_max, freq='W-SUN')
    
    print(f"Global Min: {global_min}, Global Max: {global_max}")
    print(f"Last date in global_idx: {global_idx[-1] if len(global_idx)>0 else 'None'}")
    
    app_results = calculate_moving_average(df, window=12)
    app_dict = {x['produk']: x for x in app_results}
    
    targets = [
        "Kain Background Foto Studio Kain Polos Untuk Backdrop Photo Produk",
        "Cantolan tali ikat gorden hook Lumba-Lumba",
        "Gorden Vitrase Import Dalaman Tirai Jendela"
    ]
    
    for prod in targets:
        print(f"\n{'='*50}\nPRODUK: {prod}\n{'='*50}")
        raw = df[df['produk'] == prod]
        raw_dates = set(raw['tanggal'].dt.strftime('%Y-%m-%d'))
        
        # How app does it:
        weekly = raw.set_index('tanggal')['jumlah'].resample('W').sum()
        
        print(f"\nResampled without reindex (last 3 rows):")
        print(weekly.tail(3))
        
        reindexed = weekly.reindex(global_idx, fill_value=0).reset_index()
        reindexed.columns = ['tanggal', 'jumlah']
        reindexed = reindexed.sort_values('tanggal')
        
        if prod == targets[0]:
            print("\nSELURUH 48 PERIODE MINGGUAN:")
            for _, r in reindexed.iterrows():
                dt = r['tanggal']
                dt_str = dt.strftime('%Y-%m-%d')
                val = r['jumlah']
                # Check if it was in original resampled index
                if dt in weekly.index:
                    is_fill = "Data Asli / Agregasi"
                else:
                    is_fill = "Pengisian 0"
                print(f"  {dt_str} | Jumlah: {val} | {is_fill}")
                
        last_12 = reindexed.tail(12)
        print("\n12 MINGGU TERAKHIR (Dipakai untuk MA 12):")
        for _, r in last_12.iterrows():
            print(f"  {r['tanggal'].strftime('%Y-%m-%d')} | Jumlah: {r['jumlah']}")
            
        total_12 = last_12['jumlah'].sum()
        ma_manual = total_12 / 12
        print(f"\nHasil Perhitungan Manual:")
        print(f"Total 12 Minggu = {total_12}")
        print(f"MA 12 Manual    = {total_12} / 12 = {ma_manual:.2f}")
        
        if prod in app_dict:
            app_val = app_dict[prod]
            print(f"\nHasil Aplikasi:")
            print(f"MA: {app_val['moving_avg']}")
            print(f"Prediction: {app_val['prediction']}")
            print(f"Last Week Sales: {app_val['last_week_sales']}")
            
            last_date = reindexed['tanggal'].iloc[-1]
            print(f"\nMinggu Terakhir di sistem: {last_date.strftime('%Y-%m-%d')}")
            
            # Find Dec 2, 2026 transactions
            dec2_trans = raw[raw['tanggal'] == '2026-12-02']
            print(f"\nTransaksi pada 02 Desember 2026: {len(dec2_trans)} transaksi")
            if not dec2_trans.empty:
                print(f"Total jumlah: {dec2_trans['jumlah'].sum()}")
                
if __name__ == "__main__":
    run_audit()
