# RINGKASAN AUDIT VISUAL

## MASALAH SAAT INI

```
Upload file e-commerce
    ↓
Data masuk ke cleaned_transaksi ✓
    ↓
Dashboard menampilkan data ✓
Apriori menampilkan data ✓
Moving Average menampilkan data ✓
    ↓
Menu "Transaksi" menampilkan ??? (KOSONG ✗)
```

## KENAPA KOSONG?

Menu "Transaksi" query dari tabel **transaksi** (manual input only)
Upload file data disimpan di tabel **cleaned_transaksi** (upload only)

```
TWO SEPARATE TABLES:

transaksi               cleaned_transaksi
├─ id                   ├─ id
├─ id_transaksi         ├─ session_id (FK)
├─ tanggal              ├─ id_transaksi
├─ produk               ├─ tanggal
└─ jumlah               ├─ produk
                        └─ jumlah

Status: EMPTY           Status: HAS DATA
(no manual input)       (from upload)
```

## ARSITEKTUR SAAT INI (OPSI A - NOT RECOMMENDED)

```
┌─────────────────┐        ┌──────────────────┐
│  Manual Entry   │        │  File Upload     │
│    (/input)     │        │    (/upload)     │
└────────┬────────┘        └────────┬─────────┘
         │                         │
         │ INSERT                  │ 7-stage
         ▼                         │ cleaning
    transaksi             ┌────────▼─────────┐
    (empty)               │ cleaned_transaksi│
         │                │  (has data)      │
         │                └────────┬─────────┘
         │                         │
    /data menu        Dashboard/Apriori/MA
    (shows nothing)        (shows data)
    
    ✗ PROBLEM: Two menus show different data
    ✗ Confusing for research workflow
```

## SOLUSI DIREKOMENDASIKAN (OPSI C - HYBRID)

```
┌─────────────────┐        ┌──────────────────┐
│  Manual Entry   │        │  File Upload     │
│    (/input)     │        │    (/upload)     │
└────────┬────────┘        └────────┬─────────┘
         │                         │
         │ INSERT                  │ 7-stage
         │                         │ cleaning
         │                  ┌──────▼──────┐
         │                  │INSERT BOTH: │
         │                  │1. cleaned_  │
         │                  │   transaksi │
         │                  │2. transaksi │
         │                  └──────┬──────┘
         │                         │
         ▼─────────────────────────▼
    transaksi (ALL DATA)
         │
         ├─→ /data menu (shows all data)
         │
    cleaned_transaksi (BY SESSION)
         │
         └─→ Dashboard/Apriori/MA (by session)

    ✓ BENEFIT: Menu Transaksi now populated!
    ✓ Research workflow consistent
    ✓ Minimal code change (5 lines)
    ✓ All features keep working
```

## PERBANDINGAN 3 OPSI

| Aspek | OPSI A (Current) | OPSI B (Unified) | OPSI C (Hybrid) ✅ |
|-------|----------|----------|---------|
| Transaksi menu | Kosong | Populated | Populated |
| Research workflow | ✗ Confusing | ✓ Simple | ✓ Simple |
| Code refactoring | None | Major | 5-10 lines |
| Breaking changes | — | Yes | No |
| Implementation risk | — | High | Low |
| Feature impact | — | Many affected | None |
| Session isolation | Separate | Mixed | Keeps separate |
| Data duplication | No | No | Yes (intended) |
| Backwards compat | Yes | No | Yes |
| Time to implement | — | 2-3 hours | 15 minutes |

## RENCANA IMPLEMENTASI (OPSI C)

**File: app.py**
**Route: `/process_clean_data()` → around line 450-470**

**Current code:**
```python
# Save cleaned data
conn.executemany(
    '''INSERT INTO cleaned_transaksi (session_id, id_transaksi, tanggal, produk, jumlah)
       VALUES (?, ?, ?, ?, ?)''',
    rows_clean
)
```

**Add after (NEW):**
```python
# ALSO save to transaksi for unified menu display
rows_for_menu = [
    (row['id_transaksi'], row['tanggal'], row['produk'], int(row['jumlah']))
    for _, row in df_clean.iterrows()
]
conn.executemany(
    'INSERT INTO transaksi (id_transaksi, tanggal, produk, jumlah) VALUES (?, ?, ?, ?)',
    rows_for_menu
)
```

**Result:**
- Cleaned data inserted to both tables
- Menu "Transaksi" shows all data (manual + uploads)
- Dashboard/Analysis work unchanged
- No breaking changes
- ~8 lines added

---

## DATA FLOW SETELAH OPSI C DIIMPLEMENTASI

```
MANUAL INPUT PATH:
  /input form
    ↓
  INSERT transaksi
    ↓
  /data menu displays

UPLOAD PATH:
  /upload file
    ↓
  /preview mapping
    ↓
  /process_clean_data
    ├→ INSERT cleaned_transaksi (session-tracked)
    └→ INSERT transaksi (unified display) ← NEW
    ↓
  Dashboard uses cleaned_transaksi (latest session)
  /data menu displays transaksi (all data)
```

---

## VERIFIKASI LOGIC

### CSV Content
```
id_transaksi | tanggal    | produk      | jumlah | status
TX-001       | 2024-01-15 | Kain Batik  | 10     | selesai
TX-002       | 2024-01-15 | Kain Polos  | 5      | batal
TX-003       | 2024-01-15 | Kain Batik  | 8      | selesai
```

### After 7-Stage Cleaning (Stage 3 filters by status)
```
Only kept: selesai rows
Dropped: batal rows (count: 1)

Result:
id_transaksi | tanggal    | produk     | jumlah
TX-001       | 2024-01-15 | Kain Batik | 10
TX-003       | 2024-01-15 | Kain Batik | 8
```

### After Implementation
**cleaned_transaksi** (session-based analysis):
```
session_id | id_transaksi | tanggal    | produk     | jumlah
1          | TX-001       | 2024-01-15 | Kain Batik | 10
1          | TX-003       | 2024-01-15 | Kain Batik | 8
```

**transaksi** (unified menu display):
```
id_transaksi | tanggal    | produk     | jumlah
[manual 1]   | 2024-01-10 | [product]  | [qty]
[manual 2]   | 2024-01-11 | [product]  | [qty]
TX-001       | 2024-01-15 | Kain Batik | 10    ← from upload
TX-003       | 2024-01-15 | Kain Batik | 8     ← from upload
```

**Menu "Transaksi" (/data route):**
```
SELECT * FROM transaksi ORDER BY id DESC
Result: Shows ALL 4 rows (manual + upload)
✓ PROBLEM SOLVED
```

---

## KESIMPULAN

**Status Audit: ✅ SELESAI**

**Temuan Utama:**
1. Dua tabel terpisah → dua alur data terpisah
2. Menu Transaksi query transaksi table (kosong)
3. Dashboard query cleaned_transaksi table (ada data)
4. Ini by design, bukan bug

**Rekomendasi: OPSI C (HYBRID)**
- Insert cleaned upload data ke BOTH tables
- Minimal refactoring (5-10 lines)
- Solves Transaksi menu issue
- Keeps all features working
- Low risk, high benefit

**Siap untuk implementasi! ✅**
