import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import requests

import screen_slovlex as sl


class IterSkUrlsTestCase(unittest.TestCase):
    def test_skips_records_without_odkaz_sk(self):
        raw = [{"zdroj_dat": "Sinay_Zakony", "znacka": "x", "odkaz_sk": ""}]
        self.assertEqual(list(sl.iter_sk_urls(raw)), [])

    def test_yields_populated_urls(self):
        raw = [{"zdroj_dat": "Sinay_Zakony", "znacka": "183/2006 Sb.",
                "odkaz_sk": "https://www.slov-lex.sk/x"}]
        targets = list(sl.iter_sk_urls(raw))
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0][1], "https://www.slov-lex.sk/x")


class CheckUrlTestCase(unittest.TestCase):
    def test_ok_on_200(self):
        session = MagicMock()
        resp = MagicMock(status_code=200, url="https://www.slov-lex.sk/final")
        session.get.return_value = resp
        result = sl.check_url(session, "https://www.slov-lex.sk/x")
        self.assertTrue(result["ok"])
        self.assertEqual(result["http_status"], 200)

    def test_not_ok_on_404(self):
        session = MagicMock()
        resp = MagicMock(status_code=404, url="https://www.slov-lex.sk/gone")
        session.get.return_value = resp
        result = sl.check_url(session, "https://www.slov-lex.sk/x")
        self.assertFalse(result["ok"])

    def test_not_ok_on_connection_error(self):
        session = MagicMock()
        session.get.side_effect = requests.RequestException("DNS failure")
        result = sl.check_url(session, "https://www.slov-lex.sk/x")
        self.assertFalse(result["ok"])
        self.assertIsNone(result["http_status"])
        self.assertIn("DNS failure", result["error"])


if __name__ == "__main__":
    unittest.main()
