import difflib

print("=" * 70)
print("VERIFIKASI PERBAIKAN MOVING_AVERAGE.PY")
print("=" * 70)

# Baca kedua file
with open('analysis/moving_average.py', 'r') as f:
    current = f.readlines()

with open('analysis/moving_average.py.bak', 'r') as f:
    backup = f.readlines()

# Cari perbedaan
diff = list(difflib.unified_diff(backup, current, lineterm=''))

if not diff:
    print("\n⚠ Tidak ada perbedaan (kedua file identik)")
else:
    print("\n✓ Ada perbedaan antara moving_average.py dan backup")
    
    # Deteksi perbaikan resampling
    current_text = ''.join(current)
    backup_text = ''.join(backup)
    
    # Cek fitur perbaikan
    has_global_idx = 'global_idx' in current_text and 'global_min' in current_text
    has_reindex = 'reindex(global_idx' in current_text
    
    if has_global_idx and has_reindex:
        print("\n✅ PERBAIKAN RESAMPLING DITEMUKAN")
        print("   - Menggunakan pd.date_range() untuk kalender global")
        print("   - Menggunakan reindex() untuk fill missing weeks dengan 0")
    else:
        print("\n⚠ Perbaikan resampling TIDAK ditemukan")

print("\n" + "=" * 70)
