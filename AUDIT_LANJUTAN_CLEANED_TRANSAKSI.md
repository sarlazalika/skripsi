# AUDIT LANJUTAN: Feasibility Menggunakan cleaned_transaksi untuk Menu Transaksi

## 1. PERBANDINGAN SCHEMA DETAIL

### Tabel: `transaksi` (Manual Input)
```sql
CREATE TABLE transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_transaksi TEXT NOT NULL,
    tanggal DATE NOT NULL,
    produk TEXT NOT NULL,
    jumlah INTEGER NOT NULL
)
```
- **Kolom**: 5 (id, id_transaksi, tanggal, produk, jumlah)
- **FK**: Tidak ada
- **Session tracking**: Tidak ada

### Tabel: `cleaned_transaksi` (Upload + Processed)
```sql
CREATE TABLE cleaned_transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    id_transaksi TEXT NOT NULL,
    tanggal DATE NOT NULL,
    produk TEXT NOT NULL,
    jumlah INTEGER NOT NULL,
    FOREIGN KEY(session_id) REFERENCES upload_session(id)
)
```
- **Kolom**: 6 (id, session_id, id_transaksi, tanggal, produk, jumlah)
- **FK**: session_id → upload_session(id)
- **Session tracking**: Ya (session_id)

### Field Availability Check

| Field | transaksi | cleaned_transaksi | Status |
|-------|-----------|------------------|--------|
| id_transaksi | ✓ | ✓ | SAMA |
| tanggal | ✓ | ✓ | SAMA |
| produk | ✓ | ✓ | SAMA |
| jumlah | ✓ | ✓ | SAMA |
| session_id | ✗ | ✓ | HANYA di cleaned |

**Kesimpulan: ✅ cleaned_transaksi memiliki SEMUA field yang dibutuhkan**

---

## 2. ANALISIS FITUR: CRUD & EDIT

### 2.1 Current CRUD Implementation

**CREATE (INSERT):**
```python
# app.py line 196-214: /input route
@app.route('/input', methods=['GET', 'POST'])
def input_data():
    if request.method == 'POST':
        conn.execute(
            'INSERT INTO transaksi (id_transaksi, tanggal, produk, jumlah) VALUES (?, ?, ?, ?)',
            (id_transaksi, tanggal, produk, int(jumlah))
        )
```
- Manual form entry → INSERT ke transaksi
- Tidak ada session_id
- Tidak ada validation/cleaning

**READ (SELECT):**
```python
# app.py line 217-224: /data route
@app.route('/data')
def data_transaksi():
    transaksi = conn.execute('SELECT * FROM transaksi ORDER BY id DESC').fetchall()
    return render_template('data.html', transaksi=transaksi)
```
- Query transaksi tanpa WHERE clause
- Semua data ditampilkan

**UPDATE:**
- ❌ **TIDAK ADA** route untuk UPDATE/EDIT
- ❌ **TIDAK ADA** DELETE route

**DELETE:**
- ❌ **TIDAK ADA** route untuk DELETE
- Manual cleanup hanya via database tool

### 2.2 Implikasi untuk switched ke `cleaned_transaksi`

Jika switch `/data` ke query `cleaned_transaksi`:

```python
# OPTION A: Query semua cleaned_transaksi (tanpa filter session)
transaksi = conn.execute('SELECT * FROM cleaned_transaksi ORDER BY id DESC').fetchall()

# OPTION B: Query hanya active session
active = get_active_session()
transaksi = conn.execute(
    'SELECT * FROM cleaned_transaksi WHERE session_id=? ORDER BY id DESC',
    (active['id'],)
).fetchall()
```

**Perbedaan:**
- **Option A**: Semua cleaned data dari semua uploads ditampilkan (bisa banyak)
- **Option B**: Hanya cleaned data dari latest session yang ditampilkan

**Rekomendasi awal**: Option B (konsisten dengan Dashboard/Apriori/MA yang hanya show active session)

### 2.3 CRUD Implementation untuk `cleaned_transaksi`

#### Scenario 1: INSERT Manual Data
```python
# Current: INSERT ke transaksi (validated form only)
# Proposed: INSERT ke cleaned_transaksi + UPDATE untuk set session_id
```

**Challenge**: 
- Manual input tidak punya session_id
- Bisa pakai session_id = NULL atau session_id = 0 (special marker untuk manual)
- Database schema: `session_id NOT NULL` → perlu ALTER TABLE untuk ubah jadi NULLABLE

**Solusi tanpa schema change:**
- Buat special session_id untuk manual input (misal session_id = 0)
- Atau buat tabel transaksi_manual terpisah (kompleks)

#### Scenario 2: EDIT Data
```python
# Current: Tidak ada
# Proposed: Route untuk UPDATE cleaned_transaksi
```

**Challenge untuk cleaned_transaksi:**
- Jika edit data di cleaned_transaksi → affects session data
- Preprocessing logic mengandalkan cleaned_transaksi consistency
- MAPE/validation statistics menjadi invalid jika data di-edit

**Impact Risk: 🔴 HIGH**
- Jika user edit data → stats di cleaning_stats menjadi inconsistent
- Dashboard charts akan menampilkan data yang tidak cocok dengan stats
- Audit trail hilang (kapan di-edit, siapa edit, original value apa)

#### Scenario 3: DELETE Data
```python
# Current: Tidak ada
# Proposed: Route untuk DELETE cleaned_transaksi
```

**Challenge:**
- Delete row dari cleaned_transaksi → total_clean stats jadi salah
- Preprocessing history corrupt
- Session audit trail incomplete

**Impact Risk: 🔴 HIGH**

---

## 3. ANALISIS FITUR: FILTERING

### Current Filtering Implementation

**data.html:**
- ❌ **TIDAK ADA** filter form
- ❌ **TIDAK ADA** search box
- ❌ **TIDAK ADA** date range picker
- ❌ **TIDAK ADA** product filter

**Display method:**
- Simple table with all data
- Hanya pagination via CSS (max-height + overflow-y)

### Jika switch ke cleaned_transaksi, apakah filtering bisa dilakukan?

**Teknis: ✓ YES**
```python
# Query dengan WHERE clause
WHERE session_id = ? AND tanggal BETWEEN ? AND ?
WHERE session_id = ? AND produk = ?
```

**UI: Perlu tambahan**
- Form input untuk filter criteria
- Route untuk handle filter parameters
- Template modification untuk display filter UI

**Effort Level:**
- Filter by session: trivial (already using session_id)
- Filter by date range: moderate (~20 lines)
- Filter by product: moderate (~20 lines)
- Search by id_transaksi: moderate (~20 lines)

---

## 4. ALASAN TEKNIS: Apakah HARUS pakai `transaksi`?

### Saat ini: 2 Data Paths

```
PATH A (Manual): /input → transaksi
PATH B (Upload): /upload → raw_data_temp → /process_clean → cleaned_transaksi
```

**Pertanyaan: Apakah ada alasan TEKNIS mengapa PATH A tidak bisa pakai cleaned_transaksi?**

**Analisis:**

#### Kemungkinan 1: Session tracking
- cleaned_transaksi punya session_id
- Manual input tidak dari upload session
- **Solusi**: Set session_id = 0 (atau NULL jika schema allow)

#### Kemungkinan 2: Preprocessing consistency
- cleaned_transaksi adalah output dari 7-stage preprocessing
- Manual input bypass preprocessing
- **Risk**: Data consistency (manual = raw, upload = cleaned)
- **Solusi**: Normalize manual input menggunakan same preprocessing pipeline

#### Kemungkinan 3: Audit trail
- transaksi = murni manual
- cleaned_transaksi = session-tracked uploads
- Separation for auditing purposes
- **Risk**: Mixing data trails
- **Solusi**: Add column untuk distinguish source (manual vs upload)

#### Kemungkinan 4: CRUD lifecycle
- transaksi = edit/delete allowed
- cleaned_transaksi = immutable (for analysis integrity)
- **Risk**: Corrupting analysis data
- **Solusi**: Disable edit/delete atau implement carefully

**Kesimpulan: ❌ TIDAK ADA alasan TEKNIS yang mengikat**
- Semua bisa di-solve dengan schema/logic adjustment
- Tapi ada TRADE-OFFS untuk data integrity

---

## 5. ROUTE CRUD ADJUSTMENT NEEDED

### Current Routes Related to transaksi

| Route | Method | Query | Action | Need Adjust? |
|-------|--------|-------|--------|--------------|
| /input | GET | - | Show form | No (same form) |
| /input | POST | INSERT transaksi | Save data | **YES** |
| /data | GET | SELECT transaksi | Display | **YES** |
| /import | GET/POST | Redirect /upload | Redirect | No (unchanged) |
| /export_pdf | GET | SELECT transaksi (fallback) | Export | **YES** |

### Route Adjustments Required

#### 1. /input (POST) - Input Form
**Current:**
```python
INSERT INTO transaksi (id_transaksi, tanggal, produk, jumlah) VALUES (?, ?, ?, ?)
```

**Option A: Direct insert to cleaned_transaksi**
```python
# INSERT to cleaned_transaksi with session_id = 0 (marker for manual)
INSERT INTO cleaned_transaksi (session_id, id_transaksi, tanggal, produk, jumlah)
VALUES (0, ?, ?, ?, ?)
```

**Consideration:**
- Need handle session_id = 0 in all queries
- Dashboard/Apriori/MA filter WHERE session_id = active['id'] (naturally excludes manual)
- Menu /data would show manual data separately

**Option B: Insert to both tables**
```python
INSERT INTO transaksi (...)
INSERT INTO cleaned_transaksi (session_id=0, ...)  # or NULL if schema allow
```

**Consideration:**
- More maintenance (duplicate data)
- But safer (backward compatible)

#### 2. /data (GET) - Display List
**Current:**
```python
SELECT * FROM transaksi ORDER BY id DESC
```

**If switched to cleaned_transaksi:**
```python
# Option A: All cleaned data
SELECT * FROM cleaned_transaksi ORDER BY id DESC

# Option B: Only active session
active = get_active_session()
SELECT * FROM cleaned_transaksi WHERE session_id = active['id'] ORDER BY id DESC
```

**Question: Option A vs B?**

| Aspect | Option A (All) | Option B (Active Only) |
|--------|---|---|
| Data shown | All uploads + manual | Latest session only |
| UX | Rich data, more to scroll | Clean, focused |
| Menu behavior | Different from Dashboard | Consistent with Dashboard |
| User expectation | "Show all records" | "Show current work" |
| Implementation | Query all | Query active session |

**Recommendation: Option B (consistent with Dashboard/Apriori/MA pattern)**

#### 3. /export_pdf (GET) - Export Fallback
**Current:**
```python
if active:
    SELECT ... FROM cleaned_transaksi WHERE session_id = ?
else:
    SELECT ... FROM transaksi  # fallback
```

**If cleaned_transaksi is primary:**
```python
if active:
    SELECT ... FROM cleaned_transaksi WHERE session_id = ?
else:
    SELECT ... FROM cleaned_transaksi  # export all cleaned data
    # or: flash "No active session"
```

---

## 6. IMPACT ANALYSIS: Ke Fitur Lain

### 6.1 Dashboard (/) Route

**Current:**
```python
active = get_active_session()
if active:
    SELECT COUNT(*) FROM cleaned_transaksi WHERE session_id = ?
    SELECT SUM(jumlah) FROM cleaned_transaksi WHERE session_id = ?
    # ... more queries
SELECT COUNT(*) FROM transaksi  # untuk statistik manual (tapi tidak ditampilkan)
```

**If /data uses cleaned_transaksi:**
- ✅ No change needed
- Query patterns stay same
- Session filtering unchanged

**Impact: 🟢 NONE**

### 6.2 Apriori (/apriori) Route

**Current:**
```python
active = get_active_session()
SELECT id_transaksi, produk, jumlah FROM cleaned_transaksi WHERE session_id = ?
# Build transaction baskets from this data
```

**If /data uses cleaned_transaksi:**
- ✅ No change needed
- Still queries cleaned_transaksi WHERE session_id = active['id']
- Analysis logic unchanged

**Impact: 🟢 NONE**

### 6.3 Moving Average (/moving_average) Route

**Current:**
```python
active = get_active_session()
SELECT tanggal, produk, jumlah FROM cleaned_transaksi WHERE session_id = ?
# Resample by week, calculate MA
```

**If /data uses cleaned_transaksi:**
- ✅ No change needed
- Session isolation preserved
- Resampling logic unchanged

**Impact: 🟢 NONE**

### 6.4 Preprocessing Pipeline

**Current:**
```python
# /process_clean route:
1. Read raw_data_temp
2. Apply 7-stage cleaning
3. INSERT cleaned_transaksi
4. INSERT cleaning_stats
```

**If /data uses cleaned_transaksi:**
- ✅ No change needed
- Pipeline still outputs to cleaned_transaksi
- Validation stats still apply to cleaned data

**Impact: 🟢 NONE**

### 6.5 MAPE Calculation (if exists)

**Check app.py for MAPE usage...**
```python
# grep for 'mape' or 'MAPE'
```

**If MAPE exists and queries cleaned_transaksi:**
- ✅ No change needed
- Still works with cleaned data
- Session filtering applies

**Impact: 🟢 NONE (if follows session pattern)**

### 6.6 Data Cleaning Stats (cleaning_stats table)

**Current:**
```python
# Statistics tied to upload_session
total_raw, total_clean, total_batal, etc. tied to session_id
```

**If /data queries cleaned_transaksi by session:**
- ✅ Stats remain valid for that session
- Consistency maintained
- Dashboard still shows stats correctly

**Impact: 🟢 NONE**

---

## 7. PERBANDINGAN DESAIN: OPSI A vs OPSI B

### DESIGN A: Upload → cleaned_transaksi → Semua Fitur

**Architecture:**
```
Manual Input (/input)
    ├─ Insert WHERE? (cleaned_transaksi with session_id=0?)
    ├─ Apply preprocessing? (YES or NO?)
    └─ Store in: cleaned_transaksi
    
File Upload (/upload → /process_clean)
    ├─ Apply 7-stage preprocessing
    ├─ Store in: cleaned_transaksi (with session_id)
    └─ Record stats in: cleaning_stats

Menu Transaksi (/data)
    ├─ Query: cleaned_transaksi WHERE session_id = active['id'] OR session_id = 0
    └─ Display: All data (manual + uploads)

Dashboard, Apriori, MA (/), (/apriori), (/moving_average)
    ├─ Query: cleaned_transaksi WHERE session_id = active['id']
    └─ Display: Only active session (excludes manual)

Fallback (export_pdf, etc.)
    ├─ If no active session: use cleaned_transaksi all rows
    └─ Or show message "Select active session first"
```

**Pros:**
✅ Single source of truth (cleaned_transaksi)
✅ Consistent schema across data types
✅ Easier maintenance (no duplicate tables)
✅ Natural place for CRUD if needed
✅ Menu shows all cleaned data automatically
✅ Filter/search operations simpler (all in one table)

**Cons:**
❌ Manual input needs preprocessing logic (complex)
❌ OR manual input becomes "raw" (inconsistent with uploads)
❌ Session_id = 0 semantic is non-standard
❌ Mixing manual + upload in one table (harder to audit)
❌ Need handle both data types in queries
❌ Dashboard showing only active session = confusing (why not show manual?)
❌ Database schema change needed (if session_id nullable)

**Challenges:**
1. How to handle session_id for manual data?
   - Option: session_id = 0
   - Or: ALTER TABLE to make session_id NULLABLE
   - Or: Create separate transaksi_manual table (defeats purpose)

2. Should manual data be preprocessed?
   - If YES: Need apply same cleaning logic → inconsistent with current flow
   - If NO: Manual data stays "raw" → inconsistent with upload data

3. What about Dashboard showing manual data?
   - Current: Dashboard only shows active session (session_id = active['id'])
   - If manual has session_id = 0: Dashboard never shows manual
   - User confusion: "Why menu shows manual but dashboard doesn't?"

---

### DESIGN B: Upload → cleaned_transaksi + transaksi Bersamaan

**Architecture:**
```
Manual Input (/input)
    ├─ Insert to: transaksi table
    └─ Display in: /data menu

File Upload (/upload → /process_clean)
    ├─ Apply 7-stage preprocessing
    ├─ Insert to: cleaned_transaksi (with session_id)
    ├─ Insert to: transaksi (copy of cleaned data, no session_id)
    └─ Record stats in: cleaning_stats

Menu Transaksi (/data)
    ├─ Query: transaksi (all data)
    └─ Display: Manual + cleaned uploads

Dashboard, Apriori, MA (/), (/apriori), (/moving_average)
    ├─ Query: cleaned_transaksi WHERE session_id = active['id']
    └─ Display: Only active session

Fallback (export_pdf)
    ├─ If active session: use cleaned_transaksi
    ├─ Else: use transaksi (all data)
    └─ Always has data to export
```

**Pros:**
✅ Minimal schema changes (no ALTER needed)
✅ Manual + upload data mixed in menu (user sees all)
✅ Backward compatible (transaksi still exists)
✅ Clear separation: transaksi = display, cleaned_transaksi = analysis
✅ No ambiguity about session_id
✅ Dashboard/Apriori/MA unchanged
✅ Export has fallback (always works)
✅ CRUD on transaksi = safe (doesn't break analysis)

**Cons:**
❌ Data duplication (in transaksi AND cleaned_transaksi)
❌ More maintenance (sync two tables)
❌ Potential for inconsistency if sync fails
❌ Storage inefficiency (same data twice)
❌ If edit transaksi → cleaning_stats becomes stale

**Challenges:**
1. Data duplication overhead
   - For 10,000 rows ≈ 400KB extra storage (negligible for sqlite)
   - But conceptually "unclean"

2. If user wants to edit transaksi data
   - editing transaksi doesn't affect analysis (safe)
   - But creates divergence from original cleaned data
   - Solution: Disable edit, or mark as "disconnected from session"

3. Sync during upload
   - /process_clean needs TWO INSERT statements
   - Risk: First insert succeeds, second fails
   - Solution: Transaction wrapper (both succeed or both rollback)

---

## 8. RECOMMENDATION BERDASARKAN KODE YANG ADA

### Analisis Profundis

**Point 1: Current Architecture Reveals Intent**

Code comment di app.py line ~42:
```python
# Tabel lama (input manual) — dipertahankan
# Tabel baru: data hasil cleaning (sumber utama analisis)
```

**Insight**: 
- Developers INTENTIONALLY created two separate data flows
- Called out as "old table" (transaksi) vs "main source" (cleaned_transaksi)
- Suggests deliberate separation, not accident

**Point 2: Dashboard Shows Both Worlds**

```python
# Line 164: Query cleaned_transaksi
if active:
    SELECT COUNT(*) FROM cleaned_transaksi WHERE session_id = ?

# Line 175: Query transaksi (but not displayed)
total_manual = conn.execute('SELECT COUNT(*) FROM transaksi').fetchone()[0]
```

**Insight**:
- Code queries manual data but doesn't show it
- Suggests future feature (showing manual data?)
- Or intentional: keep manual data separate from analysis

**Point 3: Export PDF Has Fallback**

```python
if active:
    SELECT ... FROM cleaned_transaksi  # primary
else:
    SELECT ... FROM transaksi  # fallback
```

**Insight**:
- Code explicitly treats cleaned_transaksi as "active session source"
- transaksi as "fallback when no session"
- Pattern shows design intent: one = analysis, one = fallback

**Point 4: No CRUD on transaksi**

- No UPDATE routes
- No DELETE routes
- Only INSERT via form

**Insight**:
- transaksi is "append-only" (write-once)
- Not designed for complex editing workflows
- Suggests: transactional audit log rather than "live data"

**Point 5: No Filtering in Templates**

- data.html has no filter UI
- cleaned_data.html has no filter UI
- All data displayed as-is

**Insight**:
- Current system shows "latest session only" (Dashboard pattern)
- Menu shows "all data" but no filtering
- Suggests: menu is informational, not analytical

---

## 9. REKOMENDASI AKHIR

### Kesimpulan

**Pertanyaan 1: Apakah cleaned_transaksi memiliki semua field?**
✅ **YA** - Memiliki id_transaksi, tanggal, produk, jumlah (sama dengan transaksi)

**Pertanyaan 2: Apakah CRUD/Edit bisa di cleaned_transaksi?**
⚠️ **BISA, TAPI RISKY** 
- INSERT: Ya (tapi perlu handle session_id)
- UPDATE: Technically ya, tapi akan corrupt stats
- DELETE: Technically ya, tapi akan corrupt stats
- Rekomendasi: Jangan edit/delete (immutable for analysis integrity)

**Pertanyaan 3: Apakah Filtering bisa langsung?**
✅ **YA** - Query sederhana dengan WHERE clause
- Need add filtering UI (form + route changes)
- ~50-100 lines code
- Moderate effort

**Pertanyaan 4: Ada alasan TEKNIS untuk keep transaksi?**
❌ **TIDAK** - Semua bisa di-solve dengan adjustment
- Tapi ada TRADE-OFFS (data consistency, audit trail, separation of concerns)

**Pertanyaan 5: Route CRUD perlu disesuaikan?**
✅ **YA** - Jika switch:
- /input route: Tentukan insert ke mana + handle session_id
- /data route: Tentukan query dengan/tanpa session filter  
- /export_pdf: Update fallback logic
- Effort: ~30-50 lines, low-moderate risk

**Pertanyaan 6: Impact ke Dashboard/MA/Apriori/etc?**
🟢 **NONE** - Jika design A dilakukan dengan hati-hati
- Queries tetap WHERE session_id = active['id']
- Analysis modules tidak berubah
- Backward compatible

**Pertanyaan 7: Bandingkan Opsi A vs B?**

| Aspek | OPSI A (cleaned only) | OPSI B (both tables) |
|-------|---|---|
| Single source | ✅ YES | ❌ NO |
| Maintenance | ✅ Simpler | ⚠️ Moderate |
| Data consistency | ⚠️ Need care | ✅ Clear separation |
| User confusion | ⚠️ High (session_id=0 semantics) | ✅ Low |
| Code changes | ⚠️ Moderate | ✅ Minimal (5-10 lines) |
| Risk level | 🔴 Moderate-High | 🟢 Low |
| Implementation time | ⚠️ 2-3 hours | ✅ 30 minutes |
| Breaking changes | 🔴 YES (schema/logic) | 🟢 NO (backward compat) |

### FINAL RECOMMENDATION: **DESIGN B (Upload → cleaned_transaksi + transaksi)**

**Alasan:**

1. **Minimal refactoring** (8 lines di /process_clean)
2. **Backward compatible** (semua existing fitur bekerja)
3. **Low risk** (tidak perlu schema changes atau logic overhaul)
4. **Clear data separation**
   - transaksi = display layer (manual + cleaned uploads)
   - cleaned_transaksi = analysis layer (immutable, session-tracked)
5. **Consistent with design intent** (architecture sudah "designed" ini way)
6. **Solves problem immediately** (Transaksi menu populates)
7. **Future-proof** (bisa migrate ke Opsi A later jika perlu)

**Implementation Detail:**

```python
# In /process_clean_data route, after INSERT to cleaned_transaksi:

# NEW: Also insert to transaksi for menu display
rows_for_transaksi = [
    (row['id_transaksi'], row['tanggal'], row['produk'], int(row['jumlah']))
    for _, row in df_clean.iterrows()
]
conn.executemany(
    'INSERT INTO transaksi (id_transaksi, tanggal, produk, jumlah) VALUES (?, ?, ?, ?)',
    rows_for_transaksi
)
```

**No other changes needed:**
- Schema: unchanged
- Routes: unchanged (except 1 route, add 1 INSERT)
- Templates: unchanged
- Analysis modules: unchanged
- Dashboard/Apriori/MA: unchanged

---

## 10. FUTURE CONSIDERATIONS

Jika di kemudian hari ingin implement filtering, CRUD, atau features lain:

**Untuk Filtering:**
- Already easy di cleaned_transaksi (WHERE session_id + other filters)
- Add form di template
- Add route handler

**Untuk CRUD (Edit/Delete):**
- OPTION B design sudah aman untuk ini
- Edit transaksi table = safe (doesn't affect analysis)
- Jika perlu affect analysis: create new session/upload

**Untuk Multiple Sessions:**
- DESIGN B naturally supports this
- Menu bisa tambahin dropdown "Select Session"
- Query: SELECT * FROM cleaned_transaksi WHERE session_id = ?

**Untuk Data Export/Archive:**
- transaksi = archive (all data ever entered)
- cleaned_transaksi = working set (current sessions)
- Both queryable separately

---

## KESIMPULAN FINAL

✅ **cleaned_transaksi BISA diguna** untuk menu Transaksi
✅ **DESIGN B adalah pilihan terbaik** (+ transaksi secara bersamaan)
✅ **Effort minimal** (~30 menit implementation)
✅ **Risk minimal** (backward compatible)
✅ **Solves problem immediately** (Transaksi menu populates)
✅ **Future-proof** (dapat di-extend untuk features lain)
