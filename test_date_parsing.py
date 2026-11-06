import sys
import unittest
from datetime import datetime
import pandas as pd
from analysis.preprocessor import _parse_date

sys.stdout.reconfigure(encoding='utf-8')

class TestDateParsing(unittest.TestCase):
    
    def test_shoope_excel_format_yyyy_mm_dd_hh_mm(self):
        """Format utama yang digunakan file Excel/CSV Shopee Marema Textile."""
        self.assertEqual(_parse_date('2026-02-11 18:09'), '2026-02-11')
        self.assertEqual(_parse_date('2026-02-12 15:07'), '2026-02-12')
        self.assertEqual(_parse_date('2026-03-11 15:46'), '2026-03-11')
        self.assertEqual(_parse_date('2026-03-12 15:39'), '2026-03-12')
        self.assertEqual(_parse_date('2025-11-01 19:34'), '2025-11-01')
        self.assertEqual(_parse_date('2025-11-14 16:12'), '2025-11-14')

    def test_no_day_month_swap_regression(self):
        """Memastikan tidak terjadi inversi hari dan bulan (pencegahan future dates)."""
        # Tanggal yang sebelumnya keliru menjadi November & Desember 2026
        self.assertNotEqual(_parse_date('2026-02-11 18:09'), '2026-11-02')
        self.assertNotEqual(_parse_date('2026-02-12 15:07'), '2026-12-02')
        self.assertNotEqual(_parse_date('2026-03-11 15:46'), '2026-11-03')
        self.assertNotEqual(_parse_date('2026-03-12 15:39'), '2026-12-03')
        self.assertNotEqual(_parse_date('2025-11-01 19:34'), '2025-01-11')

    def test_format_with_seconds(self):
        """Format YYYY-MM-DD HH:MM:SS."""
        self.assertEqual(_parse_date('2026-02-11 18:09:45'), '2026-02-11')
        self.assertEqual(_parse_date('2025-11-01 00:00:00'), '2025-11-01')

    def test_standard_iso_date_only(self):
        """Format YYYY-MM-DD murni."""
        self.assertEqual(_parse_date('2026-02-11'), '2026-02-11')
        self.assertEqual(_parse_date('2026-03-12'), '2026-03-12')
        self.assertEqual(_parse_date('2025-11-05'), '2025-11-05')

    def test_iso_with_t_delimiter(self):
        """Format ISO 8601 dengan huruf T."""
        self.assertEqual(_parse_date('2026-02-11T18:09:00'), '2026-02-11')
        self.assertEqual(_parse_date('2026-03-12T15:30:00Z'), '2026-03-12')

    def test_datetime_and_timestamp_objects(self):
        """Objek datetime murni dan pd.Timestamp hasil parsing excel pandas."""
        self.assertEqual(_parse_date(datetime(2026, 2, 11, 18, 9)), '2026-02-11')
        self.assertEqual(_parse_date(pd.Timestamp('2026-03-12 15:39:00')), '2026-03-12')

    def test_alternative_supported_formats(self):
        """Format DD/MM/YYYY, DD-MM-YYYY, teks bulan."""
        self.assertEqual(_parse_date('11/02/2026'), '2026-02-11')
        self.assertEqual(_parse_date('12-03-2026'), '2026-03-12')
        self.assertEqual(_parse_date('11 Feb 2026'), '2026-02-11')
        self.assertEqual(_parse_date('12 March 2026'), '2026-03-12')

    def test_empty_and_null_dates(self):
        """Penanganan nilai kosong, NaN, NaT, None."""
        self.assertIsNone(_parse_date(''))
        self.assertIsNone(_parse_date('   '))
        self.assertIsNone(_parse_date(None))
        self.assertIsNone(_parse_date(pd.NA))
        self.assertIsNone(_parse_date(float('nan')))
        self.assertIsNone(_parse_date('-'))
        self.assertIsNone(_parse_date('null'))
        self.assertIsNone(_parse_date('NaN'))

    def test_invalid_dates(self):
        """Penanganan string tidak valid dan tanggal tidak ada di kalender."""
        self.assertIsNone(_parse_date('2026-02-30'))  # Tanggal 30 Februari tidak ada
        self.assertIsNone(_parse_date('2026-13-01'))  # Bulan 13 tidak ada
        self.assertIsNone(_parse_date('bukan_tanggal'))
        self.assertIsNone(_parse_date('123456'))

if __name__ == '__main__':
    unittest.main()
