import pandas as pd

def calculate_moving_average(df, window=12):
    if df.empty:
        return None
    
    # 1. Ubah kolom tanggal menjadi tipe datetime
    df['tanggal'] = pd.to_datetime(df['tanggal'])
    
    # 2. Ambil batas waktu global dari keseluruhan data toko
    global_min = df['tanggal'].min()
    global_max = df['tanggal'].max()
    
    # Buat template kalender mingguan global yang mencakup seluruh rentang transaksi dari awal hingga akhir periode
    # Menggunakan resample W-SUN dari dataset agar seluruh transaksi (termasuk minggu ke-23) terangkum utuh tanpa data hilang
    global_idx = df.set_index('tanggal').resample('W-SUN').sum().index
    
    results = []
    global_errors = []
    global_apes = []
    total_validation_rows = 0
    
    for produk in df['produk'].unique():
        # Ambil data transaksi khusus produk ini
        prod_data_raw = df[df['produk'] == produk]
        
        # Resample mingguan (batas minggu konsisten W-SUN)
        prod_weekly = prod_data_raw.set_index('tanggal')['jumlah'].resample('W-SUN').sum()
        
        # Cocokkan deret dengan kalender global. Minggu yang tidak ada transaksi otomatis diisi 0.
        prod_weekly = prod_weekly.reindex(global_idx, fill_value=0).reset_index()
        prod_weekly.columns = ['tanggal', 'jumlah']
        prod_weekly = prod_weekly.sort_values('tanggal')
        
        # 3. Hitung Moving Average (Rata-rata bergerak mingguan)
        prod_weekly['moving_avg'] = prod_weekly['jumlah'].rolling(window=window).mean()
        
        # Hitung prediksi untuk minggu ke-t (rata-rata dari window sebelumnya, bebas data leakage)
        # Nilai prediksi dibatasi minimum 0 (non-negatif)
        prod_weekly['prediksi'] = prod_weekly['moving_avg'].shift(1).clip(lower=0.0)
        
        # Hitung Error untuk validasi model
        valid_rows = prod_weekly.dropna(subset=['prediksi'])
        total_validation_rows += len(valid_rows)
        
        prod_errors = []
        prod_apes = []
        for _, r in valid_rows.iterrows():
            aktual = r['jumlah']
            prediksi = r['prediksi']
            error = abs(aktual - prediksi)
            prod_errors.append(error)
            global_errors.append(error)
            
            # Penanganan MAPE ketika aktual 0:
            # Titik evaluasi dengan aktual 0 dikeluarkan dari pembagian untuk menghindari division by zero
            if aktual > 0:
                ape = error / aktual
                prod_apes.append(ape)
                global_apes.append(ape)
        
        prod_mae = sum(prod_errors) / len(prod_errors) if prod_errors else 0.0
        prod_mape = (sum(prod_apes) / len(prod_apes)) * 100 if prod_apes else None

        # Simpan deret mingguan untuk rincian tabel per minggu
        weekly_series = []
        for w_idx, r in prod_weekly.iterrows():
            tgl_str = r['tanggal'].strftime('%Y-%m-%d')
            akt_val = int(r['jumlah'])
            ma_num = round(float(r['moving_avg']), 2) if pd.notna(r['moving_avg']) else None
            pred_num = round(float(r['prediksi']), 2) if pd.notna(r['prediksi']) else None
            err_num = round(abs(akt_val - pred_num), 2) if pred_num is not None else None
            weekly_series.append({
                'week_num': w_idx + 1,
                'tanggal': tgl_str,
                'aktual': akt_val,
                'moving_avg': ma_num,
                'prediksi': pred_num,
                'error': err_num
            })

        # 4. Ambil baris terakhir (minggu paling baru) untuk data aktual dan prediksi minggu depan
        last_row = prod_weekly.iloc[-1]
        
        # Jika data bergerak masih NaN (misal data transaksi kurang dari jumlah window)
        moving_avg_val = last_row['moving_avg']
        if pd.isna(moving_avg_val):
            # Fallback ke rata-rata biasa dari semua data yang ada jika window belum terpenuhi
            moving_avg_val = prod_weekly['jumlah'].mean()
            
        results.append({
            'produk': produk,
            'last_week_sales': int(last_row['jumlah']),
            'moving_avg': round(float(moving_avg_val), 2) if not pd.isna(moving_avg_val) else 0.0,
            'prediction': max(0, int(round(float(moving_avg_val), 0))) if not pd.isna(moving_avg_val) else 0,
            'mae': round(prod_mae, 2),
            'mape': round(prod_mape, 2) if prod_mape is not None else None,
            'weekly_series': weekly_series
        })
        
    mae = sum(global_errors) / len(global_errors) if global_errors else 0.0
    mape = (sum(global_apes) / len(global_apes)) * 100 if global_apes else 0.0

    return {
        'items': results,
        'validation': {
            'mae': round(mae, 2),
            'mape': round(mape, 2),
            'n_data': total_validation_rows,
            'n_data_mape': len(global_apes),
            'n_data_zero': total_validation_rows - len(global_apes),
            'total_weeks': len(global_idx),
            'start_date': global_min.strftime('%Y-%m-%d'),
            'end_date': global_max.strftime('%Y-%m-%d')
        }
    }
