import sqlite3
import os
from datetime import datetime

DATABASE = 'database.db'

def clear_ecommerce_data():
    """Menghapus semua data e-commerce dari database"""
    
    if not os.path.exists(DATABASE):
        print(f"Database {DATABASE} tidak ditemukan.")
        return
    
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        print("=" * 50)
        print("PENGHAPUSAN DATA E-COMMERCE")
        print("=" * 50)
        
        # Tampilkan jumlah data sebelum dihapus
        cursor.execute('SELECT COUNT(*) FROM transaksi')
        count_transaksi = cursor.fetchone()[0]
        print(f"\n✓ Data di tabel 'transaksi': {count_transaksi} baris")
        
        cursor.execute('SELECT COUNT(*) FROM cleaned_transaksi')
        count_cleaned = cursor.fetchone()[0]
        print(f"✓ Data di tabel 'cleaned_transaksi': {count_cleaned} baris")
        
        cursor.execute('SELECT COUNT(*) FROM upload_session')
        count_session = cursor.fetchone()[0]
        print(f"✓ Data di tabel 'upload_session': {count_session} baris")
        
        cursor.execute('SELECT COUNT(*) FROM cleaning_stats')
        count_stats = cursor.fetchone()[0]
        print(f"✓ Data di tabel 'cleaning_stats': {count_stats} baris")
        
        total_data = count_transaksi + count_cleaned + count_session + count_stats
        
        if total_data == 0:
            print("\n⚠ Tidak ada data yang perlu dihapus.")
            conn.close()
            return
        
        # Konfirmasi
        print(f"\nTotal data yang akan dihapus: {total_data} baris")
        confirm = input("\nApakah Anda yakin ingin menghapus semua data? (ya/tidak): ").lower()
        
        if confirm in ['ya', 'y', 'yes']:
            # Hapus data dengan urutan yang tepat (foreign key constraint)
            cursor.execute('DELETE FROM cleaned_transaksi')
            print("✓ Data 'cleaned_transaksi' dihapus")
            
            cursor.execute('DELETE FROM cleaning_stats')
            print("✓ Data 'cleaning_stats' dihapus")
            
            cursor.execute('DELETE FROM upload_session')
            print("✓ Data 'upload_session' dihapus")
            
            cursor.execute('DELETE FROM transaksi')
            print("✓ Data 'transaksi' dihapus")
            
            # Reset auto-increment untuk semua tabel
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='transaksi'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='upload_session'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='cleaned_transaksi'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='cleaning_stats'")
            print("✓ Auto-increment direset")
            
            conn.commit()
            
            print("\n" + "=" * 50)
            print("✓ SEMUA DATA BERHASIL DIHAPUS")
            print("=" * 50)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"Waktu: {timestamp}\n")
            
        else:
            print("\n✗ Penghapusan dibatalkan.")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Error database: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    clear_ecommerce_data()
