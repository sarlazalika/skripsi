import sys
import sqlite3
import shutil

sys.stdout.reconfigure(encoding='utf-8')

src = 'database.db'
dst = 'database_backup_before_date_fix.db'

print(f"Membuat backup database dari {src} ke {dst}...")

# Gunakan SQLite backup API untuk backup yang aman dan konsisten
con_src = sqlite3.connect(src)
con_dst = sqlite3.connect(dst)
with con_dst:
    con_src.backup(con_dst)
con_src.close()
con_dst.close()

print("Backup selesai. Memverifikasi integritas database backup...")

con_chk = sqlite3.connect(dst)
cursor = con_chk.cursor()

# Cek integrity_check
integrity = cursor.execute("PRAGMA integrity_check").fetchone()[0]
print(f"PRAGMA integrity_check pada backup: {integrity}")
assert integrity == 'ok', "Integrity check gagal!"

# Cek jumlah tabel dan baris
expected_counts = {
    'upload_session': 3,
    'raw_data_temp': 2142,
    'cleaned_transaksi': 1779,
    'transaksi': 1673,
    'cleaning_stats': 3,
    'dataset': 1
}

for tbl, expected in expected_counts.items():
    cnt = cursor.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    print(f"Tabel {tbl}: {cnt} baris (Ekspektasi: {expected})")
    assert cnt == expected, f"Jumlah baris {tbl} tidak cocok!"

con_chk.close()
print("VERIFIKASI BACKUP SUKSES: Database backup utuh dan dapat dibaca sempurna.")
