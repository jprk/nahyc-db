import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import apply_manual_corrections as amc


class FakeCursor:
    def __init__(self, rows=(), counts=None):
        self.rows, self.counts, self.executed = list(rows), counts or {}, []

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
                         ["url", "file_path", "needs_review", "review_reason"])

    def test_the_type_changes_the_source_too(self):
        self.assertEqual(amc.affected_columns({"typ_dokumentu": "Zákon", "nazev_cz": "T"})[:3],
                         ["type_id", "source_id", "title"])


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


class DeletionTestCase(unittest.TestCase):
    def test_a_scenario_reference_blocks_the_deletion(self):
        self.assertEqual(amc.blocking_references(FakeCursor(counts={"scenario_document": 1}), 5),
                         ["scenario_document"])

    def test_deletion_removes_the_node_links_keywords_and_versions_first(self):
        cursor = FakeCursor()
        amc.delete_document(cursor, 5)
        tables = [sql.split()[2] for sql, _ in cursor.executed]
        self.assertEqual(tables, ["node_document", "DocumentKeyword", "DocumentVersion", "Document"])


if __name__ == "__main__":
    unittest.main()
