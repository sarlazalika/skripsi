# AUDIT LENGKAP: DESAIN DATABASE DAN DATA FLOW

## RINGKASAN EKSEKUTIF

**Masalah**: Menu "Transaksi" kosong setelah upload file, padahal Dashboard/Apriori/Moving Average menampilkan data dengan benar.

**Penyebab**: Aplikasi memiliki DUA ALUR DATA TERPISAH (by design):
1. **Alur Manual**: Form input → tabel `transaksi` → menu "Transaksi"
2. **Alur Upload**: File CSV → tabel `cleaned_transaksi` → Dashboard/Apriori/Moving Average

**Status**: BUKAN BUG — Desain yang disengaja, tapi perlu diperjelas untuk research workflow.

---

## BAGIAN 1: STRUKTUR DATABASE

### Tabel A: `transaksi` (Manual Input)
```sql
CREATE TABLE transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_transaksi TEXT,
    tanggal TEXT,
    produk TEXT,
    jumlah INTEGER
)
```
- **Sumber**: Form manual di `/input` route
- **Validasi**: Minimal (hanya form field validation)
- **Cleaning**: Tidak ada
- **Status Saat Ini**: KOSONG (tidak ada input manual untuk research)

### Tabel B: `cleaned_transaksi` (Upload)
```sql
CREATE TABLE cleaned_transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,                 -- Foreign key ke upload_session
    id_transaksi TEXT,
    tanggal TEXT,
    produk TEXT,
    jumlah INTEGER,
    FOREIGN KEY(session_id) REFERENCES upload_session(id)
)
```
- **Sumber**: Upload CSV/XLSX → 7-stage cleaning pipeline
- **Validasi**: Komprehensif (type check, format, status filtering)
- **Cleaning**: Ya (di `analysis/preprocessor.py`)
- **Status Saat Ini**: ADA DATA (dari file upload terakhir)

### Tabel C: `upload_session` (Metadata Upload)
```sql
CREATE TABLE upload_session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_rows INTEGER,
    column_mapping TEXT,    -- JSON: {id_transaksi, tanggal, produk, jumlah, status}
    raw_preview TEXT,       -- JSON: 50 rows pertama
    status TEXT             -- 'pending', 'cleaned'
)
```
- Mencatat setiap upload session
- Metadata untuk audit dan tracking

---

## BAGIAN 2: ALUR DATA DETAIL

### ALUR A: Input Manual

```
User fills form (/input)
    ↓
POST /input
    ↓
INSERT INTO transaksi (id_transaksi, tanggal, produk, jumlah)
    ↓
Redirect to /data
    ↓
SELECT * FROM transaksi ORDER BY id DESC
    ↓
Render data.html (menu "Transaksi")
```

**Kode Relevan**:
- Route: `app.py` line 195-214
- Template: `templates/data.html`
- Query: `SELECT * FROM transaksi ORDER BY id DESC`

---

### ALUR B: Upload & Processing (MULTI-STEP)

#### STEP 1: Upload File

```
User uploads CSV/XLSX (/upload)
    ↓
POST /upload (upload_data route)
    ↓
pd.read_csv() atau pd.read_excel()
    ↓
Auto-detect column mapping (detect_column_mapping in preprocessor.py)
    Matches CSV columns to: id_transaksi, tanggal, produk, jumlah, status
    Uses keyword matching (COLUMN_KEYWORDS dict)
    ↓
INSERT INTO upload_session (filename, total_rows, column_mapping, raw_preview, status='pending')
    ↓
INSERT INTO raw_data_temp (session_id, row_index, row_data)
    Store entire raw data as JSON
    ↓
Save session['upload_session_id'] and session['mapping']
    ↓
Redirect to /preview
```

**Kode**: `app.py` line 250-340

---

#### STEP 2: Preview & Mapping Review

```
GET /preview
    ↓
Query raw_data_temp WHERE session_id = flask_session['upload_session_id']
    ↓
Display:
  - Column mapping (auto-detected)
  - Sample data (first 20 rows)
  - Validation status
    ↓
User reviews mapping and clicks "Lanjut ke Cleaning" (atau cancel)
```

**Kode**: `app.py` line 341-400 approx

---

#### STEP 3: Data Cleaning (7-STAGE PIPELINE)

```
POST /process_clean_data
    ↓
Load raw data from raw_data_temp into pandas DataFrame
    ↓
clean_data() function (analysis/preprocessor.py line 150-220):

    STAGE 1: Rename columns to standard names
        df.rename({mapping['id_transaksi']: 'id_transaksi', ...})
        
    STAGE 2: Drop rows with missing REQUIRED fields
        Missing: id_transaksi, tanggal, produk, jumlah → DROP
        
    STAGE 3: Filter by status (if status column found)
        IF column 'status' exists:
            Keep only: selesai, completed, delivered, fulfilled, terjual, done, berhasil
            DELETE rows with: batal, pending, cancelled, etc.
            Count: n_batal (untuk statistik)
        
    STAGE 4: Normalize jumlah (quantity)
        pd.to_numeric(errors='coerce')
        Drop NaN values
        Keep only jumlah > 0
        Cast to int
        
    STAGE 5: Normalize tanggal (date)
        Parse multiple date formats (DD/MM/YYYY, YYYY-MM-DD, etc.)
        Drop unparseable dates
        
    STAGE 6: Normalize strings
        id_transaksi.strip()
        produk.strip()
        
    STAGE 7: SELECT only 4 standard columns
        df_clean = df[['id_transaksi', 'tanggal', 'produk', 'jumlah']]
        ⚠️  Status column DROPPED (used for filtering, not stored)
    ↓
INSERT INTO cleaned_transaksi (session_id, id_transaksi, tanggal, produk, jumlah)
    All cleaned rows
    ↓
INSERT INTO cleaning_stats:
    - total_raw
    - total_clean
    - total_batal
    - total_invalid
    - cleaning_reasons (JSON array)
    - has_status_col
    - pct_valid
    ↓
UPDATE upload_session SET status='cleaned'
    ↓
Redirect to /cleaned_data
```

**Kode**: `analysis/preprocessor.py` line 180-220 (clean_data function)
**Kode**: `app.py` line 430-520 (process_clean_data route)

---

#### STEP 4: View Cleaned Data

```
GET /cleaned_data
    ↓
active = get_active_session()
    Query: SELECT * FROM upload_session WHERE status='cleaned' ORDER BY id DESC LIMIT 1
    (Only shows LATEST session)
    ↓
SELECT * FROM cleaned_transaksi WHERE session_id = active['id'] ORDER BY tanggal ASC
    ↓
SELECT cleaning_stats WHERE session_id = active['id']
    ↓
Render cleaned_data.html
    - Shows cleaned data table
    - Shows statistics
    - Shows buttons: Lihat Dashboard, Apriori, Moving Average
```

**Kode**: `app.py` line 522-560

---

### ALUR C: Dashboard & Analysis

#### Dashboard (/)

```
GET /
    ↓
active = get_active_session()
    (Only LATEST cleaned session)
    ↓
IF active session exists:
    SELECT SUM(jumlah) by month FROM cleaned_transaksi WHERE session_id = active['id']
    SELECT COUNT(DISTINCT produk) FROM cleaned_transaksi WHERE session_id = active['id']
    SELECT strftime('%Y-%m', tanggal) as bulan, SUM(jumlah) as total
        FROM cleaned_transaksi WHERE session_id = active['id']
    ↓
Render index.html with:
    - Total cleaned records
    - Unique products
    - Sales trend (6 months)
    - Pie chart by product
```

**Kode**: `app.py` line 138-175

---

#### Apriori Analysis (/apriori)

```
GET /apriori
    ↓
active = get_active_session()
    ↓
SELECT tanggal, produk, jumlah FROM cleaned_transaksi WHERE session_id = active['id']
    ↓
analysis/apriori.py:
    - Create transaction basket by date
    - Apply Apriori algorithm
    - Generate frequent itemsets
    - Calculate support, confidence, lift
    ↓
Render apriori.html
```

**Kode**: `app.py` line 560-600

---

#### Moving Average (/moving_average)

```
GET /moving_average
    ↓
active = get_active_session()
    ↓
SELECT tanggal, produk, jumlah FROM cleaned_transaksi WHERE session_id = active['id']
    ↓
analysis/moving_average.py:
    - Resample by week
    - Apply moving average (window = 3 default)
    - Forecast next week
    ↓
Render moving_average.html
```

**Kode**: `app.py` line 600-630

---

## BAGIAN 3: CRITICAL INSIGHTS

### Insight 1: Status Column Filtering

**CSV Upload dapat memiliki kolom "status":**
```
id_transaksi | tanggal    | produk | jumlah | status
TX001        | 2024-01-15 | Kain A | 10     | selesai
TX002        | 2024-01-15 | Kain B | 5      | batal
TX003        | 2024-01-15 | Kain A | 8      | selesai
```

**Proses Cleaning (Stage 3):**
- Baris dengan status "selesai/completed/delivered" → KEEP
- Baris dengan status "batal/cancelled/pending" → DELETE (counted as n_batal)

**Output di cleaned_transaksi:**
```
session_id | id_transaksi | tanggal    | produk | jumlah
1          | TX001        | 2024-01-15 | Kain A | 10
1          | TX003        | 2024-01-15 | Kain A | 8
```
⚠️ Status column TIDAK ada di output (sudah difilter)

---

### Insight 2: get_active_session() Design Pattern

```python
def get_active_session():
    return conn.execute(
        "SELECT * FROM upload_session WHERE status='cleaned' ORDER BY id DESC LIMIT 1"
    ).fetchone()
```

**Behavior:**
- Returns ONLY latest cleaned session
- If multiple uploads exist: shows only latest
- Older data persists in database but hidden from UI
- Feature: Can access older sessions if needed (modify UI)
- Current workflow: Always work with latest session

---

### Insight 3: Two Separate Data Paths

| Aspek | Manual Path | Upload Path |
|-------|----------|----------|
| **Source** | Form input | CSV/XLSX file |
| **Storage** | transaksi | cleaned_transaksi |
| **Display** | Menu "Transaksi" | Dashboard/Apriori/MA |
| **Validation** | Form only | 7-stage cleaning |
| **Status Query** | Langsung tampil | Hanya latest session |
| **Use Case** | Quick entry | Batch analysis |

---

## BAGIAN 4: DESAIN RECOMMENDATION

### OPSI A: Current Design (SEPARATE PATHS)

**Arsitektur:**
```
Manual Entry → transaksi → /data menu
Upload File → cleaned_transaksi → Dashboard/Apriori/MA
```

**Pros:**
✓ Clear separation of concerns
✓ Audit trail (manual vs upload)
✓ Status filtering only on upload
✓ No changes needed

**Cons:**
✗ User confusion (two different menus showing different data)
✗ Transaksi menu always empty for upload-only workflow
✗ Code duplication (two similar data tables)
✗ Inconsistent UX (manual ≠ upload paths)

**Verdict: TIDAK COCOK untuk research workflow**

---

### OPSI B: Unified Upload+Manual Path

**Arsitektur:**
```
Manual Entry → transaksi
Upload File → /process_clean → transaksi
Dashboard/Apriori/MA → transaksi (same table)
```

**Changes Needed:**
1. Remove cleaned_transaksi table
2. In `/process_clean`: INSERT to transaksi instead of cleaned_transaksi
3. Update Dashboard/Apriori/MA to query transaksi instead of cleaned_transaksi
4. Handle session_id somehow (maybe add to transaksi as optional column)
5. Update all templates

**Pros:**
✓ Single source of truth
✓ Simpler data model
✓ Consistent UX

**Cons:**
✗ Major refactoring required (affects many routes)
✗ Loses session-based data isolation
✗ Session tracking becomes complex
✗ Breaking changes to existing features
✗ More risk of bugs

**Verdict: BANYAK REFACTORING, HIGH RISK**

---

### OPSI C: Hybrid Approach (RECOMMENDED) ✅

**Arsitektur:**
```
Manual Entry 
    ↓
    INSERT → transaksi
    
Upload File
    ↓
    [7-stage cleaning]
    ↓
    INSERT → cleaned_transaksi (dengan session_id untuk history)
    PLUS
    INSERT → transaksi (untuk unified menu display)
    ↓
Dashboard/Apriori/MA
    ├→ Query cleaned_transaksi WHERE session_id=latest (session isolation)
    │  (keeps current implementation working)
    └→ or optionally: query transaksi (if switching later)
    
Menu "Transaksi" → SELECT * FROM transaksi
    (shows all data: manual + uploads)
```

**Implementation Steps:**
1. After cleaning pipeline completes, insert cleaned data to BOTH tables:
   ```python
   # Existing: INSERT to cleaned_transaksi (keep for session history)
   conn.executemany(
       'INSERT INTO cleaned_transaksi (session_id, id_transaksi, tanggal, produk, jumlah) VALUES (...)',
       rows_clean
   )
   
   # NEW: Also insert to transaksi for unified display
   rows_transaksi = [(row['id_transaksi'], row['tanggal'], row['produk'], int(row['jumlah'])) 
                      for _, row in df_clean.iterrows()]
   conn.executemany(
       'INSERT INTO transaksi (id_transaksi, tanggal, produk, jumlah) VALUES (?, ?, ?, ?)',
       rows_transaksi
   )
   ```

2. Menu "Transaksi" automatically shows all data (manual + uploads)

3. Dashboard/Analysis continue working unchanged (using cleaned_transaksi)

4. Benefits:
   - ✓ Minimal code changes (2-3 lines in /process_clean)
   - ✓ Transaksi menu populates automatically
   - ✓ Keeps session isolation for analysis
   - ✓ Backwards compatible
   - ✓ Audit trail maintained
   - ✓ Research workflow friendly
   - ✓ Low risk implementation

**Code Location for Change:**
File: `app.py`, Function: `process_clean_data()`, After line 450-460
Insert additional executemany() call to transaksi table

---

## BAGIAN 5: ALUR SEHARUSNYA (OPSI C)

```
┌─ MANUAL INPUT ──────────────────────┐
│  GET /input                         │
│  POST /input (form submission)      │
│  → INSERT transaksi (id, id_t...)   │
│  → Redirect /data                   │
└────────────────────────────────────┘
         ↓
    ┌────────┐
    │transaksi table
    │(All manual data)
    └────────┘
         ↓
    /data menu
    (Shows: transaksi)

┌─ UPLOAD & ANALYSIS ─────────────────┐
│  GET /upload                        │
│  POST /upload → raw_data_temp       │
│  GET /preview → (review mapping)    │
│  POST /process_clean_data           │
│    → 7-stage cleaning               │
│    → INSERT cleaned_transaksi       │
│    → INSERT transaksi (NEW)         │
│    → INSERT cleaning_stats          │
│  → Redirect /cleaned_data           │
└────────────────────────────────────┘
         ↓
    ┌────────────────────────┐
    │cleaned_transaksi       │ ← keeps session_id
    │(Upload data + cleaned) │
    └────────────────────────┘
         ↓
    Dashboard/Apriori/MA
    (Uses: cleaned_transaksi WHERE session_id=latest)

    ┌────────┐
    │transaksi table
    │(All data: manual + uploads)
    └────────┘
         ↓
    /data menu
    (Shows: transaksi - now populated!)
```

---

## KESIMPULAN

**Rekomendasi: OPSI C (HYBRID APPROACH)**

**Alasan:**
1. **Minimal refactoring**: Only add 5-10 lines of code
2. **Solves the problem**: Transaksi menu populates from uploads
3. **Keeps current features working**: Dashboard/Analysis unchanged
4. **Maintains data integrity**: Session history preserved
5. **Research-friendly**: Single menu for all data analysis
6. **Low risk**: No breaking changes
7. **Future-proof**: Can migrate fully to Option B later if needed

**Next Steps:**
1. Modify `app.py` `/process_clean_data` route (after line 450)
2. Add second INSERT to transaksi table
3. Test: Upload file → Check /data menu → Verify data appears
4. Done!

---

## FILES TO MODIFY

**File: app.py**
- Route: `/process_clean_data()` 
- Location: Around line 450-470 (after INSERT to cleaned_transaksi)
- Change: Add INSERT to transaksi table
- Impact: ~5-10 lines added, no breaking changes

**NO changes needed:**
- Database schema (tables already exist)
- Routes (all routes work as-is)
- Templates (all templates work as-is)
- Analysis modules (unchanged)
- UI (unchanged)
