import unittest
import time
import re
from app import app

class TestPdfExportComprehensive(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_export_pdf_attributes_and_content(self):
        response = self.client.get('/export_pdf')
        
        # 1. Status Code
        self.assertEqual(response.status_code, 200)
        
        # 2. Content-Type
        self.assertEqual(response.content_type, 'application/pdf')
        
        # 3. Dynamic filename pattern matching: Laporan_Restok_Marema_Textile_dd-mm-yy_HHMMSS.pdf
        cd = response.headers.get('Content-Disposition', '')
        pattern = r'attachment;\s*filename="Laporan_Restok_Marema_Textile_\d{2}-\d{2}-\d{2}_\d{6}\.pdf"'
        self.assertTrue(re.match(pattern, cd), f"Content-Disposition '{cd}' does not match pattern {pattern}")
        
        # Extract filename
        fn_match = re.search(r'filename="([^"]+)"', cd)
        self.assertIsNotNone(fn_match)
        filename = fn_match.group(1)
        
        # Extract timestamp from filename: dd-mm-yy_HHMMSS
        ts_match = re.search(r'Laporan_Restok_Marema_Textile_(\d{2})-(\d{2})-(\d{2})_(\d{2})(\d{2})(\d{2})\.pdf', filename)
        self.assertIsNotNone(ts_match)
        d, m, y, H, M, S = ts_match.groups()
        expected_date_str = f"{d}/{m}/{y}"

        # 4. Non-empty data & signature
        pdf_bytes = response.data
        self.assertGreater(len(pdf_bytes), 1500)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))
        self.assertIn(b'%%EOF', pdf_bytes)
        self.assertIn(b'/Root', pdf_bytes)
        self.assertIn(b'/Pages', pdf_bytes)

        # 5. Consistency check: The date dd/mm/yy, WIB, and Restock Headers must be in PDF text
        pdf_text = pdf_bytes.decode('latin1', errors='ignore')
        
        self.assertIn(expected_date_str, pdf_text, f"Date {expected_date_str} not found in PDF")
        self.assertIn("WIB", pdf_text, "WIB timezone marker not found in PDF")
        self.assertIn("Marema Textile", pdf_text)
        self.assertIn("Rekomendasi Restok", pdf_text)

    def test_two_downloads_different_timestamps(self):
        res1 = self.client.get('/export_pdf')
        cd1 = res1.headers.get('Content-Disposition', '')
        
        time.sleep(1.1)  # Tunggu > 1 detik agar detik berbeda
        
        res2 = self.client.get('/export_pdf')
        cd2 = res2.headers.get('Content-Disposition', '')
        
        self.assertNotEqual(cd1, cd2, f"Expected distinct filenames, got {cd1} and {cd2}")
        print(f"Verified distinct filenames:\n 1: {cd1}\n 2: {cd2}")

if __name__ == '__main__':
    unittest.main()
