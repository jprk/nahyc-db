import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import apply_manual_corrections as amc


class FakeCursor:
    def __init__(self, rows=(), counts=None):
        self.rows, self.counts, self.executed = list(rows), counts or {}, []
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))
        self.last = " ".join(sql.split())

    def fetchone(self):
        for table, count in self.counts.items():
            if f"FROM {table} " in self.last:
                return (count,)
        return (0,)

    def fetchall(self):
        return self.rows


class AffectedColumnsTestCase(unittest.TestCase):
    def test_gestor_changes_the_source_and_the_review_flags(self):
        self.assertEqual(amc.affected_columns({"gestor": ["X"]}), ["source_id", "needs_review", "review_reason"])

    def test_a_new_address_changes_the_url_and_the_file(self):
        self.assertEqual(amc.affected_columns({"odkaz_hlavni": "u", "zdroj_autoritativni_url": ""}),
                         ["url", "file_path", "zdroj_autoritativni_url", "needs_review", "review_reason"])

    def test_the_authoritative_title_has_its_own_column_and_platnost_is_the_effective_date(self):
        self.assertEqual(amc.affected_columns({"nazev_autoritativni": "T", "platnost": "1.1.2015"})[:3],
                         ["title", "nazev_autoritativni", "effective_date"])

    def test_the_type_changes_the_source_too(self):
        self.assertEqual(amc.affected_columns({"typ_dokumentu": "Zákon", "nazev_cz": "T"})[:3],
                         ["type_id", "source_id", "title"])


class RenamedDesignationTestCase(unittest.TestCase):
    def test_a_new_designation_changes_the_identifier_and_the_file(self):
        # the full-text manifest is keyed by the designation (fetch_fulltext.manifest_key())
        self.assertEqual(amc.affected_columns({"znacka": "492/2010 Z. z."})[:3], ["identifier", "title", "file_path"])


class CorrectedItemTestCase(unittest.TestCase):
    def test_a_record_already_renamed_still_gets_the_pinned_slug(self):
        entry = {"changes": {"znacka": "ČSN ISO 19880-1", "slug": "csn-en-iso-19880-1"}}
        record = {"znacka": "ČSN ISO 19880-1", "nazev_cz": "Plynný vodík"}
        item = amc.corrected_item(record, "ČSN EN ISO 19880-1", entry)
        self.assertEqual(item["slug"], "csn-en-iso-19880-1")
        self.assertEqual(record, {"znacka": "ČSN ISO 19880-1", "nazev_cz": "Plynný vodík"})

    def test_a_record_found_by_its_key_is_corrected_as_before(self):
        item = amc.corrected_item({"znacka": "A 1", "gestor": ["X"]}, "A 1", {"changes": {"gestor": ["Y"]}})
        self.assertEqual(item["gestor"], ["Y"])


class RecordsByKeyTestCase(unittest.TestCase):
    def test_rows_sharing_a_znacka_are_kept_together_and_records_without_key_skipped(self):
        records = [{"znacka": "A"}, {"znacka": "A"}, {"znacka": "", "odkaz_hlavni": ""}]
        self.assertEqual(len(amc.records_by_key(records)["A"]), 2)
        self.assertEqual(list(amc.records_by_key(records)), ["A"])


class FindDocumentsTestCase(unittest.TestCase):
    def test_an_exclusion_also_finds_the_english_variant(self):
        cursor = FakeCursor(rows=[(128,), (1472,)])
        self.assertEqual(amc.find_documents(cursor, "(EU) 2018/546", {"exclude": True}, None), [128, 1472])
        self.assertEqual(cursor.executed[0][1], ["(EU) 2018/546", "(EU) 2018/546 [EN]"])

    def test_a_corrected_znacka_is_looked_up_as_well(self):
        cursor = FakeCursor(rows=[(87,)])
        amc.find_documents(cursor, "(EU) 2023/1234", {"changes": {"znacka": "(EU) 2024/1735"}}, None)
        self.assertEqual(cursor.executed[0][1], ["(EU) 2023/1234", "(EU) 2024/1735"])

    def test_a_record_without_znacka_is_found_by_its_old_or_new_address(self):
        from fulltext_keys import url_designation
        old, new = "https://www.slov-lex.sk/x/", "https://eur-lex.europa.eu/y"

        class Cursor(FakeCursor):
            results = [[], [(78, old), (79, new), (80, "https://elsewhere")]]

            def fetchall(self):
                return self.results.pop(0)

        record = {"znacka": "", "odkaz_hlavni": old, "zdroj_autoritativni_url": new}
        self.assertEqual(amc.find_documents(Cursor(), url_designation(old), {"changes": {}}, record), [78, 79])

    def test_a_znacka_key_is_not_looked_up_by_address(self):
        cursor = FakeCursor(rows=[])
        self.assertEqual(amc.find_documents(cursor, "458/2000 Sb.", {"changes": {}}, {"znacka": "458/2000 Sb."}), [])
        self.assertEqual(len(cursor.executed), 1)


class TitleKeyTestCase(unittest.TestCase):
    def test_a_record_without_znacka_and_address_is_found_by_its_title(self):
        from fulltext_keys import title_designation
        title = "Smernica  o\xa0plyne"

        class Cursor(FakeCursor):
            results = [[], [(83, "Iná smernica"), (84, title)]]

            def fetchall(self):
                return self.results.pop(0)

        key = title_designation(title)
        self.assertEqual(amc.find_documents(Cursor(), key, {"changes": {"znacka": "(EU) 1/2 [SK]"}}, None), [84])

    def test_once_corrected_it_is_found_by_its_new_identifier(self):
        cursor = FakeCursor(rows=[(84,)])
        self.assertEqual(amc.find_documents(cursor, "title-0000abcd", {"changes": {"znacka": "Z"}}, None), [84])
        self.assertEqual(len(cursor.executed), 1)


class MergeTestCase(unittest.TestCase):
    def test_every_link_moves_to_the_survivor_before_the_document_goes(self):
        cursor = FakeCursor()
        amc.merge_document(cursor, 92, 139)
        statements = [sql for sql, _ in cursor.executed]
        self.assertTrue(statements[0].startswith("DELETE FROM document_relation WHERE (from_document_id"))
        self.assertEqual(cursor.executed[0][1], (92, 139, 139, 92))
        moved = [sql.split()[1] if sql.split()[1] != "IGNORE" else sql.split()[2]
                 for sql in statements if sql.startswith("UPDATE")]
        self.assertEqual(moved, ["document_relation", "document_relation", "node_document", "scenario_document",
                                 "DocumentSourceCategory", "node_activation_rule", "ReviewItem", "DocumentCandidate"])
        self.assertIn("UPDATE IGNORE DocumentSourceCategory SET document_id = %s WHERE document_id = %s", statements)
        self.assertIn("DELETE FROM DocumentSourceCategory WHERE document_id = %s", statements)
        self.assertEqual(statements[-2:], ["DELETE FROM DocumentVersion WHERE document_id = %s",
                                           "DELETE FROM Document WHERE id = %s"])
        for sql, params in cursor.executed[1:]:
            if sql.startswith("UPDATE"):
                self.assertEqual(params, (139, 92))

    def test_the_slug_of_a_renamed_document_is_the_one_a_rebuild_gives(self):
        rows = [(75, "98/2004 Z. z.", "Zákon", "98-2004-z-z"), (76, "1/2000 Z. z.", "Iný", "1-2000-z-z")]
        self.assertEqual(amc.wanted_slug(FakeCursor(rows=rows), 75, "492/2010 Z. z.", "Zákon"), "492-2010-z-z")

    def test_a_slug_another_document_has_is_not_taken(self):
        rows = [(75, "98/2004 Z. z.", "Zákon", "98-2004-z-z"), (76, "X", "Iný", "492-2010-z-z")]
        self.assertIsNone(amc.wanted_slug(FakeCursor(rows=rows), 75, "492/2010 Z. z.", "Zákon"))


class DeletionTestCase(unittest.TestCase):
    def test_a_scenario_reference_blocks_the_deletion(self):
        self.assertEqual(amc.blocking_references(FakeCursor(counts={"scenario_document": 1}), 5),
                         ["scenario_document"])

    def test_deletion_removes_the_node_links_keywords_and_versions_first(self):
        cursor = FakeCursor()
        amc.delete_document(cursor, 5)
        tables = [sql.split()[2] for sql, _ in cursor.executed]
        self.assertEqual(tables, ["node_document", "DocumentSourceCategory", "DocumentVersion", "Document"])


if __name__ == "__main__":
    unittest.main()
