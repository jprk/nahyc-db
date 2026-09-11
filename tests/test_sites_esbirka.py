import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from sites.esbirka import eli_from_znacka, reference_url_from_znacka, verify


def _fake_session(citace_values):
    session = MagicMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "results": {"bindings": [{"citace": {"value": v}} for v in citace_values]}
    }
    session.get.return_value = response
    return session


class EliFromZnackaTestCase(unittest.TestCase):
    def test_parses_a_real_czech_law_znacka(self):
        self.assertEqual(eli_from_znacka("283/2021 Sb."),
                          "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2021/283")

    def test_non_czech_law_shapes_are_none(self):
        self.assertIsNone(eli_from_znacka("ISO 14687"))
        self.assertIsNone(eli_from_znacka("(EU) 2019/692"))
        self.assertIsNone(eli_from_znacka("124/2000 Z. z."))  # Slovak, not Czech
        self.assertIsNone(eli_from_znacka(""))
        self.assertIsNone(eli_from_znacka(None))


class ReferenceUrlFromZnackaTestCase(unittest.TestCase):
    def test_builds_the_human_facing_url(self):
        self.assertEqual(reference_url_from_znacka("458/2000 Sb."),
                          "https://e-sbirka.gov.cz/sb/2000/458")

    def test_non_czech_law_is_none(self):
        self.assertIsNone(reference_url_from_znacka("ISO 14687"))


class VerifyTestCase(unittest.TestCase):
    def test_confirmed_citation_returns_reference_url(self):
        session = _fake_session(["283/2021 Sb."])
        self.assertEqual(verify("283/2021 Sb.", session=session),
                          "https://e-sbirka.gov.cz/sb/2021/283")

    def test_mismatched_citation_is_none(self):
        # Real ELI node exists but its own citation doesn't match ours --
        # never trusted blindly.
        session = _fake_session(["999/2021 Sb."])
        self.assertIsNone(verify("283/2021 Sb.", session=session))

    def test_no_binding_at_all_is_none(self):
        session = _fake_session([])
        self.assertIsNone(verify("283/2021 Sb.", session=session))

    def test_non_czech_law_never_queries(self):
        session = _fake_session(["should not matter"])
        self.assertIsNone(verify("ISO 14687", session=session))
        session.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
