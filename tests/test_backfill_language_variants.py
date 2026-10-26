import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import backfill_language_variants as bf


class FakeCursor:
    def __init__(self, fetchone=None, fetchall=None):
        self._one, self._all, self.executed = fetchone, fetchall, []

    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class EnsureRelationTypeTestCase(unittest.TestCase):
    def test_the_enum_is_extended_when_it_lacks_the_type(self):
        cursor = FakeCursor(fetchone=("enum('AMENDS','ADOPTS')",))
        self.assertTrue(bf.ensure_relation_type(cursor))
        self.assertIn("ENUM('AMENDS','ADOPTS','TRANSLATION_OF')", cursor.executed[-1][0])

    def test_nothing_is_changed_when_the_type_is_there(self):
        cursor = FakeCursor(fetchone=("enum('AMENDS','TRANSLATION_OF')",))
        self.assertFalse(bf.ensure_relation_type(cursor))
        self.assertEqual(len(cursor.executed), 1)


class PlanTestCase(unittest.TestCase):
    def test_each_relation_pairs_the_two_records_with_their_documents(self):
        records = [{"znacka": "A"}, {"znacka": "A [EN]"}]
        relations = [{"from_identifier": "A [EN]", "to_identifier": "A"}]
        cursor = FakeCursor(fetchall=[("A", 7)])
        self.assertEqual(bf.plan(cursor, records, relations), [({"znacka": "A"}, {"znacka": "A [EN]"}, 7, None)])


class ColumnValuesTestCase(unittest.TestCase):
    def test_the_values_follow_the_column_order_and_blank_overlays_become_null(self):
        prepared = {c: c for c in bf.UPDATED_COLUMNS}
        item = {"zdroj_dat": "Haltuf_Dokumenty", "nazev_autoritativni": "", "popis_autoritativni": "d"}
        values = dict(zip(bf.UPDATED_COLUMNS, bf.column_values(prepared, item)))
        self.assertEqual((values["title"], values["zdroj_dat"], values["nazev_autoritativni"],
                          values["popis_autoritativni"]), ("title", "Haltuf_Dokumenty", None, "d"))


if __name__ == "__main__":
    unittest.main()
