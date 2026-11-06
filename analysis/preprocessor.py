"""
preprocessor.py — Modul Preprocessing Data E-Commerce
=====================================================
Melakukan mapping kolom otomatis, validasi, dan cleaning data
tanpa memerlukan format khusus dari platform e-commerce tertentu.
"""

import pandas as pd
import re
from datetime import datetime


# ─────────────────────────────────────────────
# KAMUS MAPPING KOLOM OTOMATIS (Fleksibel)
# ─────────────────────────────────────────────
COLUMN_KEYWORDS = {
    'id_transaksi': [
        'no. pesanan', 'no pesanan', 'nomor pesanan', 'order id', 'order_id',
        'id pesanan', 'id transaksi', 'id_transaksi', 'no. order', 'invoice',
        'kode transaksi', 'kode pesanan', 'transaction id', 'nomor transaksi',
        'no transaksi', 'no.', 'order number', 'receipt', 'ref', 'referensi'
    ],
    'tanggal': [
        'tanggal', 'tgl', 'date', 'waktu', 'time', 'tanggal transaksi',
        'tanggal pembelian', 'tanggal pesanan', 'order date', 'purchase date',
        'tgl transaksi', 'tgl pesanan', 'tanggal pembayaran', 'payment date',
        'tanggal selesai', 'tanggal order'
    ],
    'produk': [
        'nama produk', 'produk', 'product', 'nama barang', 'barang',
        'item', 'sku', 'product name', 'nama item', 'deskripsi produk',
        'kode produk', 'product sku', 'nama', 'description', 'goods name',
        'nama barang/produk', 'produk/barang', 'jenis produk'
    ],
    'jumlah': [
        'jumlah', 'qty', 'quantity', 'kuantitas', 'jumlah beli',
        'jumlah produk', 'jumlah pembelian', 'total qty', 'unit',
        'banyak', 'amount', 'jumlah item', 'quantity ordered'
    ],
    'status': [
        'status', 'status pesanan', 'status transaksi', 'order status',
        'kondisi', 'state', 'status order', 'status pembayaran',
        'payment status', 'transaction status'
    ]
}

# Kata kunci status yang dianggap VALID (selesai)
STATUS_VALID_KEYWORDS = [
    'selesai', 'completed', 'sukses', 'success', 'delivered',
    'terkirim', 'diterima', 'done', 'finish', 'finished', 'complete'
]

# Kata kunci status yang dianggap BATAL/INVALID
STATUS_BATAL_KEYWORDS = [
    'batal', 'dibatalkan', 'cancel', 'cancelled', 'canceled',
    'refund', 'dikembalikan', 'retur', 'return', 'failed', 'gagal',
    'ditolak', 'rejected', 'expired', 'kadaluarsa'
]


def _normalize_colname(name: str) -> str:
    """Normalisasi nama kolom: lowercase, hapus spasi berlebih."""
    return re.sub(r'\s+', ' ', str(name).strip().lower())


def detect_column_mapping(df: pd.DataFrame) -> dict:
    """
    Deteksi otomatis mapping kolom dari DataFrame mentah ke kolom standar.
    
    Returns:
        dict berisi {target_col: source_col} atau {target_col: None} jika tidak ditemukan.
    """
    raw_cols = {_normalize_colname(c): c for c in df.columns}
    mapping = {target: None for target in COLUMN_KEYWORDS}

    for target, keywords in COLUMN_KEYWORDS.items():
        for kw in keywords:
            kw_norm = _normalize_colname(kw)
            # Exact match dulu
            if kw_norm in raw_cols:
                mapping[target] = raw_cols[kw_norm]
                break
        
        # Jika belum ditemukan, coba partial match (substring)
        if mapping[target] is None:
            for kw in keywords:
                kw_norm = _normalize_colname(kw)
                for col_norm, col_orig in raw_cols.items():
                    if kw_norm in col_norm or col_norm in kw_norm:
                        mapping[target] = col_orig
                        break
                if mapping[target] is not None:
                    break

    return mapping


def validate_structure(df: pd.DataFrame, mapping: dict) -> dict:
    """
    Validasi apakah kolom wajib ditemukan.
    
    Returns:
        dict berisi {'valid': bool, 'missing': list, 'warnings': list}
    """
    required = ['id_transaksi', 'tanggal', 'produk', 'jumlah']
    missing = [col for col in required if mapping.get(col) is None]
    warnings = []

    if mapping.get('status') is None:
        warnings.append(
            'Kolom status tidak ditemukan. Semua transaksi akan dianggap valid (tidak ada filtering status).'
        )

    return {
        'valid': len(missing) == 0,
        'missing': missing,
        'warnings': warnings
    }


def _parse_date(val) -> str | None:
    """Coba parse berbagai format tanggal ke YYYY-MM-DD secara akurat."""
    if pd.isna(val):
        return None
    
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.strftime('%Y-%m-%d')
    
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ('none', 'nan', 'nat', 'null', '-', ''):
        return None
    
    # 1. Format ISO berawalan Tahun: YYYY-MM-DD atau YYYY/MM/DD
    # Jangan pernah menerapkan dayfirst=True pada format yang diawali tahun
    iso_match = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})', val_str)
    if iso_match:
        year, month, day = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        try:
            return datetime(year, month, day).strftime('%Y-%m-%d')
        except ValueError:
            return None
    
    # 2. Format tanggal umum yang dicoba secara eksplisit
    date_formats = [
        '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d',
        '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M', '%Y/%m/%d',
        '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y',
        '%d-%m-%Y %H:%M:%S', '%d-%m-%Y %H:%M', '%d-%m-%Y',
        '%d %B %Y', '%d %b %Y', '%B %d, %Y',
        '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ',
        '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %H:%M', '%m/%d/%Y',
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(val_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # 3. Fallback: pandas to_datetime dengan kontrol dayfirst yang aman
    try:
        # Hanya gunakan dayfirst=True jika string diawali 1-2 digit (misal: DD/MM/YYYY)
        is_day_first = bool(re.match(r'^\d{1,2}[-/]', val_str))
        dt = pd.to_datetime(val_str, dayfirst=is_day_first, errors='coerce')
        if pd.notna(dt):
            return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    
    return None


def clean_data(df: pd.DataFrame, mapping: dict) -> tuple[pd.DataFrame, dict]:
    """
    Jalankan proses cleaning lengkap pada DataFrame mentah.
    
    Args:
        df: DataFrame mentah dari file e-commerce
        mapping: dict hasil detect_column_mapping()
    
    Returns:
        (cleaned_df, stats_dict)
    """
    total_raw = len(df)
    reasons = []
    
    # ── Langkah 1: Rename kolom ke nama standar ──
    rename_map = {v: k for k, v in mapping.items() if v is not None}
    df_work = df.rename(columns=rename_map).copy()
    
    # Pastikan kolom wajib ada (walau hasil rename)
    required_cols = ['id_transaksi', 'tanggal', 'produk', 'jumlah']
    for col in required_cols:
        if col not in df_work.columns:
            df_work[col] = None

    # ── Langkah 2: Drop baris di mana kolom wajib kosong ──
    before = len(df_work)
    df_work = df_work.dropna(subset=['id_transaksi', 'tanggal', 'produk', 'jumlah'])
    dropped_empty = before - len(df_work)
    if dropped_empty > 0:
        reasons.append(f'{dropped_empty} baris dibuang karena kolom wajib kosong')

    # ── Langkah 3: Filter status (jika kolom status ditemukan) ──
    status_col = 'status' if 'status' in df_work.columns else None
    n_batal = 0
    
    if status_col:
        def is_valid_status(s):
            s_norm = str(s).strip().lower()
            # Jika mengandung kata valid → simpan
            for kw in STATUS_VALID_KEYWORDS:
                if kw in s_norm:
                    return True
            return False
        
        mask_valid = df_work[status_col].apply(is_valid_status)
        n_batal = (~mask_valid).sum()
        df_work = df_work[mask_valid].copy()
        
        if n_batal > 0:
            reasons.append(f'{n_batal} transaksi dibuang karena status Batal/tidak valid')
    
    # ── Langkah 4: Normalisasi kolom jumlah ──
    before = len(df_work)
    df_work['jumlah'] = pd.to_numeric(df_work['jumlah'], errors='coerce')
    df_work = df_work.dropna(subset=['jumlah'])
    df_work = df_work[df_work['jumlah'] > 0]
    df_work['jumlah'] = df_work['jumlah'].astype(int)
    dropped_qty = before - len(df_work)
    if dropped_qty > 0:
        reasons.append(f'{dropped_qty} baris dibuang karena jumlah tidak valid (kosong/nol/negatif)')

    # ── Langkah 5: Normalisasi kolom tanggal ──
    before = len(df_work)
    df_work['tanggal'] = df_work['tanggal'].apply(_parse_date)
    df_work = df_work.dropna(subset=['tanggal'])
    dropped_date = before - len(df_work)
    if dropped_date > 0:
        reasons.append(f'{dropped_date} baris dibuang karena format tanggal tidak dapat dibaca')

    # ── Langkah 6: Normalisasi string ──
    df_work['id_transaksi'] = df_work['id_transaksi'].astype(str).str.strip()
    df_work['produk'] = df_work['produk'].astype(str).str.strip()

    # ── Langkah 6.5: Exclude Produk Non-Item ──
    before = len(df_work)
    non_items_keywords = ['klip backdrop', 'ongkos jahit']
    def is_non_item(prod):
        p_lower = str(prod).lower()
        return any(kw in p_lower for kw in non_items_keywords)
    
    mask_item = ~df_work['produk'].apply(is_non_item)
    df_work = df_work[mask_item].copy()
    dropped_non_item = before - len(df_work)
    if dropped_non_item > 0:
        reasons.append(f'{dropped_non_item} baris dibuang karena merupakan produk non-item (Klip Backdrop/Ongkos Jahit)')

    # ── Langkah 7: Pilih hanya kolom standar ──
    df_clean = df_work[['id_transaksi', 'tanggal', 'produk', 'jumlah']].copy()
    df_clean = df_clean.reset_index(drop=True)

    total_clean = len(df_clean)
    total_removed = total_raw - total_clean

    stats = {
        'total_raw': total_raw,
        'total_clean': total_clean,
        'total_batal': n_batal,
        'total_invalid': total_removed - n_batal,
        'total_removed': total_removed,
        'cleaning_reasons': reasons,
        'has_status_col': status_col is not None,
        'pct_valid': round((total_clean / total_raw * 100), 1) if total_raw > 0 else 0
    }

    return df_clean, stats


def get_preview_data(df: pd.DataFrame, n: int = 20) -> list[dict]:
    """Kembalikan N baris pertama sebagai list of dict untuk preview template."""
    return df.head(n).fillna('').to_dict('records')


def get_mapping_display(df: pd.DataFrame, mapping: dict) -> list[dict]:
    """
    Siapkan data mapping untuk ditampilkan di template.
    
    Returns:
        list of dict: [{target, source, found, sample_value}]
    """
    result = []
    label_map = {
        'id_transaksi': 'ID Transaksi',
        'tanggal': 'Tanggal',
        'produk': 'Nama Produk',
        'jumlah': 'Jumlah',
        'status': 'Status Transaksi'
    }
    required_fields = ['id_transaksi', 'tanggal', 'produk', 'jumlah', 'status']
    
    for target in required_fields:
        source = mapping.get(target)
        sample = ''
        if source and source in df.columns:
            sample_val = df[source].dropna().head(1)
            sample = str(sample_val.values[0]) if len(sample_val) > 0 else ''
        
        result.append({
            'target': target,
            'target_label': label_map.get(target, target),
            'source': source or '—',
            'found': source is not None,
            'required': target != 'status',
            'sample': sample[:60] + '...' if len(sample) > 60 else sample
        })
    
    return result
