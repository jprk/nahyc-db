import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import candidates as cd
import citation_closure as cc


class DesignationTestCase(unittest.TestCase):
    def test_the_designation_reads_back_as_the_same_key(self):
        for key, kind, expected in (("CZ:505/1990", None, "505/1990 Sb."),
                                    ("EU:2019/943", "regulation", "(EU) 2019/943"),
                                    ("EU:2009/715", "regulation", "(ES) č. 715/2009"),
                                    ("EU:2003/87", "directive", "2003/87/ES"),
                                    ("EU:1989/391", "directive", "1989/391/EHS"),
                                    ("EU:2024/1788", "directive", "2024/1788/EU")):
            designation = cd.designation(key, kind)
            self.assertEqual(designation, expected)
            self.assertEqual(cc.own_keys(designation, None), {key}, designation)

    def test_addresses_and_types(self):
        self.assertEqual(cd.document_url("CZ:505/1990"), "https://www.zakonyprolidi.cz/cs/1990-505")
        self.assertEqual(cd.document_url("EU:2003/87", "directive"),
                         "https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX:32003L0087")
        self.assertIsNone(cd.document_url("EU:2003/87"))
        self.assertEqual(cd.czech_type("Zákon o metrologii"), "Zákon")
        self.assertEqual(cd.czech_type("Nařízení vlády o technických požadavcích"), "Nařízení vlády")
        self.assertEqual(cd.czech_type("Vyhláška o jakosti"), "Vyhláška")
        self.assertEqual(cd.czech_type(None), "Nezařazeno")
        self.assertEqual(cd.kind_from_celex("32019R0943"), "regulation")


ROW = {"key": "EU:2003/87", "family": "EU", "in_database": False, "cited_by": 15, "amendment_share": 0.0,
       "kind": "directive", "citing_ids": [1, 2], "context": "…směrnice 2003/87/ES…"}


class FromChecksTestCase(unittest.TestCase):
    def test_closure_candidates_are_missing_cited_enough_not_amendments_and_not_repealed(self):
        cache = {"EU:2003/87": {"status": "účinný", "celex": "32003L0087"}, "EU:1994/9": {"status": "zrušený"}}
        rows = [ROW, {**ROW, "key": "EU:1994/9"}, {**ROW, "key": "EU:2000/1", "cited_by": 1},
                {**ROW, "key": "EU:2000/2", "amendment_share": 0.9}, {**ROW, "key": "EU:2000/3", "in_database": True},
                {**ROW, "key": "NORM:EN 590", "family": "NORM"}]
        found = cd.from_closure(rows, cache)
        self.assertEqual([c["candidate_key"] for c in found], ["EU:2003/87"])
        self.assertEqual((found[0]["source"], found[0]["validity_status"], found[0]["evidence"]["celex"]),
                         ("citation", "účinný", "32003L0087"))

    def test_validity_candidates_are_missing_successors_with_the_documents_they_repealed(self):
        cache = {"CZ:133/2010": {"status": "zrušený", "repealed_by": ["CZ:516/2020"]},
                 "CZ:183/2006": {"status": "zrušený", "repealed_by": ["CZ:283/2021"]}}
        documents = [(60, "133/2010 Sb.", ""), (46, "183/2006 Sb.", ""), (122, "283/2021 Sb.", "")]
        found = cd.from_validity(documents, cache)
        self.assertEqual([(c["candidate_key"], c["evidence"]["repeals_ids"]) for c in found], [("CZ:516/2020", [60])])

    def test_complete_fills_the_document_metadata(self):
        candidate = cd.from_closure([ROW], {"EU:2003/87": {"status": "účinný", "celex": "32003L0087"}})[0]
        done = cd.complete(candidate, {"EU:2003/87": ("32003L0087", "Směrnice 2003/87/ES o povolenkách")})
        self.assertEqual((done["designation"], done["document_type"], done["jurisdikce"], done["title"]),
                         ("2003/87/ES", "Směrnice EU", "EU", "Směrnice 2003/87/ES o povolenkách"))
        self.assertTrue(done["url"].endswith("CELEX:32003L0087"))


class FakeCursor:
    def __init__(self, row=None):
        self.row, self.sql = row, []

    def execute(self, sql, params=None):
        self.sql.append((" ".join(sql.split())[:40], params))

    def fetchone(self):
        return self.row


class UpsertTestCase(unittest.TestCase):
    CANDIDATE = {"candidate_key": "EU:2003/87", "source": "citation", "evidence": {"citing_ids": [1]}, "cited_by": 15}

    def test_a_new_candidate_is_inserted(self):
        cursor = FakeCursor(None)
        self.assertEqual(cd.upsert(cursor, self.CANDIDATE), "inserted")
        self.assertTrue(cursor.sql[-1][0].startswith("INSERT INTO DocumentCandidate"))

    def test_an_open_candidate_only_gets_fresh_evidence(self):
        cursor = FakeCursor({"id": 7, "status": "deferred"})
        self.assertEqual(cd.upsert(cursor, self.CANDIDATE), "updated")
        self.assertTrue(cursor.sql[-1][0].startswith("UPDATE DocumentCandidate SET evidence"))

    def test_a_decided_candidate_is_left_alone(self):
        for status in ("accepted", "rejected"):
            cursor = FakeCursor({"id": 7, "status": status})
            self.assertEqual(cd.upsert(cursor, self.CANDIDATE), "kept")
            self.assertEqual(len(cursor.sql), 1)


if __name__ == "__main__":
    unittest.main()
