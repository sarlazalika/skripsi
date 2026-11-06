import sqlite3
import random
from datetime import datetime, timedelta

DATABASE = 'database.db'

def populate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Kosongkan data lama untuk membuat data dummy baru yang sesuai bidang usaha Marema Textile
    cursor.execute('DELETE FROM transaksi')
    
    # Daftar produk asli Marema Textile sesuai info user
    # kain, gorden, batang, kain waterproof, kain kanvas, kain blacu, fitras, tikar piknik
    products = [
        "Kain Katun Rayon",
        "Gorden Minimalis",
        "Batang Gorden Rolllet",
        "Kain Waterproof Parasut",
        "Kain Kanvas Premium",
        "Kain Blacu Tebal",
        "Fitras (Vitrase) Putih",
        "Tikar Piknik Lipat"
    ]
    
    # Kita buat transaksi realistis dengan kecenderungan pola pembelian (untuk Apriori):
    # Pola 1: Pembelian Gorden Minimalis + Batang Gorden Rolllet + Fitras (Vitrase) Putih (Paket dekorasi jendela)
    # Pola 2: Pembelian Kain Kanvas Premium + Kain Blacu Tebal (Bahan kerajinan/tas/pouch)
    # Pola 3: Pembelian Tikar Piknik Lipat + Kain Waterproof Parasut (Perlengkapan outdoor/wisata)
    
    transactions = []
    start_date = datetime(2026, 1, 1)
    
    # Buat sekitar 50 transaksi unik (TR-2026-001 s/d TR-2026-050)
    for i in range(1, 55):
        tr_id = f"TR-2026-{i:03d}"
        
        # Sebaran tanggal dari Januari hingga Mei 2026
        month_offset = (i - 1) // 11  # sebaran merata ~11 transaksi per bulan
        day_offset = random.randint(1, 28)
        tr_date = (start_date + timedelta(days=month_offset * 30.5 + day_offset)).strftime('%Y-%m-%d')
        
        chosen_products = []
        p_type = random.random()
        
        if p_type < 0.35:
            # Combo Dekorasi Jendela (Sangat sering dibeli bersamaan)
            chosen_products.append(("Gorden Minimalis", random.randint(2, 6)))
            chosen_products.append(("Batang Gorden Rolllet", random.randint(2, 6)))
            if random.random() < 0.8:  # 80% kemungkinan beli Fitras juga
                chosen_products.append(("Fitras (Vitrase) Putih", random.randint(2, 5)))
                
        elif p_type < 0.60:
            # Combo Kerajinan / Bahan Jahit
            chosen_products.append(("Kain Kanvas Premium", random.randint(5, 15)))
            chosen_products.append(("Kain Blacu Tebal", random.randint(5, 20)))
            if random.random() < 0.3:
                chosen_products.append(("Kain Katun Rayon", random.randint(4, 10)))
                
        elif p_type < 0.80:
            # Combo Outdoor / Rekreasi
            chosen_products.append(("Tikar Piknik Lipat", random.randint(1, 3)))
            chosen_products.append(("Kain Waterproof Parasut", random.randint(3, 10)))
            
        else:
            # Pembelian eceran acak
            item1 = random.choice(products)
            chosen_products.append((item1, random.randint(2, 12)))
            if random.random() < 0.4:
                item2 = random.choice([p for p in products if p != item1])
                chosen_products.append((item2, random.randint(2, 8)))
                
        # Simpan ke daftar transaksi
        for prod, qty in chosen_products:
            transactions.append((tr_id, tr_date, prod, qty))
            
    # Masukkan data ke database
    cursor.executemany(
        'INSERT INTO transaksi (id_transaksi, tanggal, produk, jumlah) VALUES (?, ?, ?, ?)',
        transactions
    )
    
    conn.commit()
    total = cursor.execute('SELECT COUNT(*) FROM transaksi').fetchone()[0]
    conn.close()
    print(f"Berhasil membuat dan memasukkan {total} data transaksi spesifik Marema Textile ke database!")

if __name__ == '__main__':
    populate()
