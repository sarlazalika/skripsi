import unittest
import sqlite3
from app import app

class TestFinalApp(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_database_counts(self):
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM cleaned_transaksi')
        cleaned_cnt = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM transaksi')
        manual_cnt = c.fetchone()[0]
        conn.close()
        self.assertEqual(cleaned_cnt, 1779, f"Cleaned count must be 1779, got {cleaned_cnt}")
        self.assertEqual(manual_cnt, 1673, f"Manual count must be 1673, got {manual_cnt}")

    def test_index_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('Jumlah Unit Terjual', html)
        self.assertIn('/rekomendasi', html)

    def test_cleaned_data_route(self):
        response = self.client.get('/cleaned_data')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertTrue('1779' in html or '1,779' in html)

    def test_moving_average_route(self):
        response = self.client.get('/moving_average')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('MAE', html)
        self.assertIn('MAPE', html)
        self.assertIn('12.1', html)
        self.assertIn('176.98', html)
        self.assertIn('132', html)

    def test_apriori_route(self):
        response = self.client.get('/apriori')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertTrue('1366' in html or '1,366' in html)
        self.assertIn('Stand background', html)
        self.assertIn('Kain Background', html)

    def test_rekomendasi_route(self):
        response = self.client.get('/rekomendasi')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('Sistem Rekomendasi Restok', html)
        self.assertIn('Restok + Pendamping', html)
        self.assertIn('Restok Mandiri', html)
        self.assertIn('Tunda Pengadaan', html)

if __name__ == '__main__':
    unittest.main()
