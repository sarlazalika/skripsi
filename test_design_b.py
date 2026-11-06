#!/usr/bin/env python3
"""Test script untuk verify DESIGN B implementation"""

import sqlite3
import json

DATABASE = 'database.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def main():
    conn = get_db()
    
    print("=" * 80)
    print("TEST DESIGN B IMPLEMENTATION")
    print("=" * 80)
    
    # Check tabel transaksi
    print("\n[1] Checking transaksi table:")
    transaksi_count = conn.execute('SELECT COUNT(*) as cnt FROM transaksi').fetchone()['cnt']
    print(f"    Total rows in transaksi: {transaksi_count}")
    
    if transaksi_count > 0:
        print("    Sample data from transaksi (first 5):")
        samples = conn.execute(
            'SELECT id, id_transaksi, tanggal, produk, jumlah FROM transaksi LIMIT 5'
        ).fetchall()
        for row in samples:
            print(f"      {row['id']}: {row['id_transaksi']} | {row['tanggal']} | {row['produk']} | {row['jumlah']}")
    
    # Check tabel cleaned_transaksi
    print("\n[2] Checking cleaned_transaksi table:")
    cleaned_count = conn.execute('SELECT COUNT(*) as cnt FROM cleaned_transaksi').fetchone()['cnt']
    print(f"    Total rows in cleaned_transaksi: {cleaned_count}")
    
    if cleaned_count > 0:
        print("    Sample data from cleaned_transaksi (first 5):")
        samples = conn.execute(
            'SELECT id, session_id, id_transaksi, tanggal, produk, jumlah FROM cleaned_transaksi LIMIT 5'
        ).fetchall()
        for row in samples:
            print(f"      {row['id']}: session={row['session_id']}, {row['id_transaksi']} | {row['tanggal']} | {row['produk']} | {row['jumlah']}")
    
    # Check upload_session
    print("\n[3] Checking upload_session table:")
    sessions = conn.execute('SELECT * FROM upload_session ORDER BY id DESC LIMIT 3').fetchall()
    print(f"    Latest sessions (max 3):")
    for session in sessions:
        print(f"      Session {session['id']}: {session['filename']} (status={session['status']})")
    
    # Check for duplicates in transaksi
    print("\n[4] Checking for duplicates in transaksi:")
    duplicates = conn.execute('''
        SELECT id_transaksi, tanggal, produk, jumlah, COUNT(*) as cnt
        FROM transaksi
        GROUP BY id_transaksi, tanggal, produk, jumlah
        HAVING COUNT(*) > 1
    ''').fetchall()
    
    if duplicates:
        print(f"    Found {len(duplicates)} duplicate combinations:")
        for dup in duplicates:
            print(f"      {dup['id_transaksi']} | {dup['tanggal']} | {dup['produk']} | {dup['jumlah']} => appears {dup['cnt']} times")
    else:
        print("    ✅ No duplicates found")
    
    # Verify data consistency: count in cleaned should match count in transaksi (from uploads)
    print("\n[5] Data consistency check:")
    latest_session = conn.execute(
        'SELECT * FROM upload_session WHERE status="cleaned" ORDER BY id DESC LIMIT 1'
    ).fetchone()
    
    if latest_session:
        session_id = latest_session['id']
        cleaned_in_session = conn.execute(
            'SELECT COUNT(*) as cnt FROM cleaned_transaksi WHERE session_id=?',
            (session_id,)
        ).fetchone()['cnt']
        
        print(f"    Latest cleaned session: {latest_session['filename']} (ID={session_id})")
        print(f"    Rows in cleaned_transaksi for this session: {cleaned_in_session}")
        print(f"    Total rows in transaksi: {transaksi_count}")
        
        # Note: transaksi should have >= cleaned_in_session (because of manual input + uploads)
        if transaksi_count >= cleaned_in_session:
            print(f"    ✅ transaksi has all cleaned data (and possibly manual data)")
        else:
            print(f"    ⚠️  WARNING: transaksi has fewer rows than cleaned_transaksi for latest session")
    else:
        print("    No cleaned sessions found")
    
    # Check dashboard data
    print("\n[6] Dashboard statistics:")
    dash_stats = conn.execute('''
        SELECT 
            (SELECT COUNT(*) FROM cleaned_transaksi WHERE session_id IN (SELECT id FROM upload_session WHERE status='cleaned' ORDER BY id DESC LIMIT 1)) as cleaned_total,
            (SELECT COUNT(*) FROM transaksi) as transaksi_total,
            (SELECT COUNT(DISTINCT produk) FROM cleaned_transaksi WHERE session_id IN (SELECT id FROM upload_session WHERE status='cleaned' ORDER BY id DESC LIMIT 1)) as produk_count
    ''').fetchone()
    
    print(f"    Cleaned data (active session): {dash_stats['cleaned_total']}")
    print(f"    Transaksi data: {dash_stats['transaksi_total']}")
    print(f"    Unique products (active): {dash_stats['produk_count']}")
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    if transaksi_count > 0 and cleaned_count > 0:
        print("✅ DESIGN B Implementation Successful!")
        print(f"   - transaksi table has {transaksi_count} rows")
        print(f"   - cleaned_transaksi table has {cleaned_count} rows")
        print("   - Menu Transaksi should now display data")
    elif cleaned_count > 0 and transaksi_count == 0:
        print("❌ DESIGN B Implementation FAILED")
        print(f"   - cleaned_transaksi has {cleaned_count} rows")
        print(f"   - BUT transaksi has {transaksi_count} rows (should have data)")
        print("   - Menu Transaksi will still be empty")
    else:
        print("⚠️ No data in either table - upload a file first")
    
    conn.close()

if __name__ == '__main__':
    main()
