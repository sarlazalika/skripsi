import unittest
import sqlite3
import pandas as pd
from app import app
from analysis.preprocessor import _parse_date
from analysis.moving_average import calculate_moving_average
from analysis.apriori import perform_apriori
from analysis.rekomendasi import get_restock_recommendations

class TestComprehensiveMarema(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    # 1. Integritas Database
    def test_database_integrity(self):
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM cleaned_transaksi')
        clean_count = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM transaksi')
        manual_count = c.fetchone()[0]
        c.execute('SELECT MIN(tanggal), MAX(tanggal) FROM cleaned_transaksi')
        min_date, max_date = c.fetchone()
        
        # Cek anomali tanggal masa depan (Nov-Des 2026)
        c.execute("SELECT COUNT(*) FROM cleaned_transaksi WHERE tanggal >= '2026-11-01'")
        future_count = c.fetchone()[0]
        conn.close()

        self.assertEqual(clean_count, 1779, f"Cleaned transaksi harus 1.779, didapat {clean_count}")
        self.assertEqual(manual_count, 1673, f"Data input manual harus 1.673, didapat {manual_count}")
        self.assertEqual(min_date, '2025-11-01')
        self.assertEqual(max_date, '2026-04-02')
        self.assertEqual(future_count, 0, "Tidak boleh ada tanggal anomali masa depan (>= Nov 2026)")

    # 2. Dashboard Route
    def test_dashboard_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('Jumlah Unit Terjual', html)
        self.assertIn('1779', html)
        self.assertIn('1673', html)
        self.assertIn('/rekomendasi', html)

    # 3. Cleaned Data Route
    def test_cleaned_data_route(self):
        response = self.client.get('/cleaned_data')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('1779', html)
        self.assertIn('2142', html)
        self.assertIn('250', html)
        self.assertIn('113', html)
        self.assertIn('Detail Proses Preprocessing', html)

    # 4. Moving Average (Default Window = 12)
    def test_moving_average_default(self):
        response = self.client.get('/moving_average')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        
        # Validasi numerik pada HTML
        self.assertIn('12.1', html)       # MAE: 12.10
        self.assertIn('176.98', html)     # MAPE: 176.98%
        self.assertIn('132', html)        # Total 132 titik evaluasi
        self.assertIn('52', html)         # 52 titik dengan aktual > 0
        self.assertIn('80', html)         # 80 titik aktual = 0
        self.assertIn('23 minggu', html)

    # 5. Moving Average (Alternative Window = 4)
    def test_moving_average_alternative_window(self):
        response = self.client.get('/moving_average?window=4')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        # Total weeks 23, window 4 -> 19 evaluation weeks * 12 products = 228 titik
        self.assertIn('228', html)

    # 6. Apriori Default (min_support=0.005, min_confidence=0.5)
    def test_apriori_default(self):
        response = self.client.get('/apriori')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('1366', html)
        self.assertIn('8', html)
        self.assertIn('Stand background', html)
        self.assertIn('Kain Background', html)
        self.assertIn('85.7%', html)
        self.assertIn('1.037', html)

    # 7. Apriori No Rules (High Threshold)
    def test_apriori_no_rules(self):
        response = self.client.get('/apriori?min_support=0.5&min_confidence=0.9')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('Tidak ada aturan yang terbentuk', html)

    # 8. Rekomendasi Restok Route
    def test_rekomendasi_route(self):
        response = self.client.get('/rekomendasi')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('Sistem Rekomendasi Restok', html)
        self.assertIn('Restok + Pendamping', html)
        self.assertIn('Restok Mandiri', html)
        self.assertIn('Tunda Pengadaan', html)
        self.assertIn('Stand background foto studio ukuran 3m', html)
        self.assertIn('konfirmasi volume pengadaan riil memerlukan verifikasi stok gudang', html.lower())

    # 9. Parsing Tanggal ISO format
    def test_date_parsing_iso_format(self):
        # YYYY-MM-DD
        self.assertEqual(_parse_date('2026-03-12'), '2026-03-12')
        self.assertEqual(_parse_date('2025-11-05'), '2025-11-05')
        # YYYY-MM-DD HH:MM
        self.assertEqual(_parse_date('2026-03-12 14:30'), '2026-03-12')
        # Empty / Invalid
        self.assertIsNone(_parse_date(''))
        self.assertIsNone(_parse_date('invalid_date'))

if __name__ == '__main__':
    unittest.main()
