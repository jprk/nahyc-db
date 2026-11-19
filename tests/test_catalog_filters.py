"""app/catalog_filters.py (doc/MPO_PRIPOMINKY.md, krok 2): jurisdiction filter,
EU act subtypes in the type menu, the synonym dictionary and the grouping of the
původce menu — and how app.py turns them into SQL. No database."""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from app import catalog_filters as cf  # noqa: E402


class JurisdictionTestCase(unittest.TestCase):
    def test_empty_or_unknown_means_the_default(self):
        self.assertEqual(cf.resolve_jurisdiction("", default="vse"), "vse")
        self.assertEqual(cf.resolve_jurisdiction("nesmysl", default="bez-sk"), "bez-sk")
        self.assertEqual(cf.resolve_jurisdiction("cz", default="bez-sk"), "cz")

    def test_the_default_is_a_known_choice(self):
        self.assertIn(cf.DEFAULT_JURISDICTION, cf.JURISDICTIONS)

    def test_everything_adds_no_condition(self):
        self.assertEqual(cf.jurisdiction_condition("vse"), ("", []))

    def test_without_slovakia_keeps_documents_without_a_jurisdiction(self):
        condition, params = cf.jurisdiction_condition("bez-sk")
        self.assertIn("IS NULL", condition)
        self.assertEqual(params, ["SK"])

    def test_other_states_exclude_the_four_named_groups(self):
        condition, params = cf.jurisdiction_condition("jine")
        self.assertEqual(condition.count("%s"), len(params))
        self.assertEqual(set(params), {"CZ", "SK", "EU", "mezinárodní"})

    def test_menu_puts_the_default_under_the_empty_value(self):
        options = cf.jurisdiction_options(default="bez-sk")
        self.assertEqual(options[0], ("", "Vše kromě Slovenska"))
        values = [v for v, _ in options]
        self.assertNotIn("bez-sk", values)
        self.assertIn("vse", values)
        self.assertEqual(len(values), len(cf.JURISDICTIONS))


class TypeFilterTestCase(unittest.TestCase):
    def test_plain_type_id(self):
        self.assertEqual(cf.split_type_filter("5"), ("5", ""))

    def test_subtype(self):
        self.assertEqual(cf.split_type_filter("podtyp-delegated"), ("", "delegated"))
        self.assertEqual(cf.split_type_filter("podtyp-implementing"), ("", "implementing"))

    def test_unknown_subtype_is_ignored(self):
        self.assertEqual(cf.split_type_filter("podtyp-nic"), ("", ""))


ENTRIES = [
    {"label": "RED III", "aliases": ["RED III"], "search_terms": [], "identifiers": ["(EU) 2023/2413"]},
    {"label": "RED II", "aliases": ["RED II"], "search_terms": [], "identifiers": ["(EU) 2018/2001"]},
    {"label": "RFNBO", "aliases": ["RFNBO"], "search_terms": ["nebiologického původu"],
     "identifiers": ["(EU) 2023/1184", "(EU) 2018/2001"]},
]


class SynonymMatchingTestCase(unittest.TestCase):
    def labels(self, query):
        return [e["label"] for e in cf.match_synonyms(query, ENTRIES)]

    def test_case_and_spacing_do_not_matter(self):
        self.assertEqual(self.labels("rfnbo"), ["RFNBO"])
        self.assertEqual(self.labels("  red\xa0 iii "), ["RED III"])

    def test_whole_words_only(self):
        self.assertEqual(self.labels("RED III"), ["RED III"])
        self.assertEqual(self.labels("RED II"), ["RED II"])
        self.assertEqual(self.labels("hundred"), [])

    def test_alias_inside_a_longer_query(self):
        self.assertEqual(self.labels("certifikace RFNBO vodíku"), ["RFNBO"])

    def test_empty_query_matches_nothing(self):
        self.assertEqual(self.labels(""), [])

    def test_expansion_merges_without_duplicates(self):
        terms, identifiers = cf.expansion(ENTRIES)
        self.assertEqual(terms, ["nebiologického původu"])
        self.assertEqual(identifiers, ["(EU) 2023/2413", "(EU) 2018/2001", "(EU) 2023/1184"])


class SynonymDictionaryTestCase(unittest.TestCase):
    """The committed data/search_synonyms.json. That every identifier exists in
    the database is checked by tests/test_search.py."""

    @classmethod
    def setUpClass(cls):
        cls.entries = cf.load_synonyms()

    def test_every_entry_is_well_formed(self):
        for entry in self.entries:
            self.assertTrue(entry["label"].strip())
            self.assertTrue(entry["aliases"], entry["label"])
            self.assertIsInstance(entry.get("search_terms", []), list)
            self.assertTrue(entry.get("search_terms") or entry.get("identifiers"), entry["label"])

    def test_no_alias_belongs_to_two_entries(self):
        seen = {}
        for entry in self.entries:
            for alias in entry["aliases"]:
                key = cf.normalize(alias)
                self.assertNotIn(key, seen, f"{alias!r} in {entry['label']!r} and {seen.get(key)!r}")
                seen[key] = entry["label"]

    def expanded(self, query):
        return cf.expansion(cf.match_synonyms(query, self.entries))

    def test_mpo_queries(self):
        """The queries named in doc/MPO_PRIPOMINKY.md, krok 2."""
        _, rfnbo = self.expanded("RFNBO")
        self.assertTrue({"(EU) 2023/1184", "(EU) 2023/1185", "(EU) 2023/2413"} <= set(rfnbo))
        self.assertEqual(self.expanded("AFIR")[1], ["(EU) 2023/1804"])
        self.assertEqual(self.expanded("RED III")[1], ["(EU) 2023/2413"])
        self.assertEqual(self.expanded("RED II")[1], ["(EU) 2018/2001"])
        self.assertIn("165/2012 Sb.", self.expanded("LEX OZE")[1])
        self.assertIn("165/2012 Sb.", self.expanded("Lex OZE II")[1])

    def test_reloads_after_the_file_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "s.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"entries": ENTRIES[:1]}, f)
            self.assertEqual(len(cf.load_synonyms(path)), 1)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"entries": ENTRIES}, f)
            os.utime(path, (1, 1))
            self.assertEqual(len(cf.load_synonyms(path)), 3)


class SourceGroupsTestCase(unittest.TestCase):
    CONFIG = {
        "groups": [{"key": "cz", "label": "Česká republika"}, {"key": "eu", "label": "Evropská unie"},
                   {"key": "std", "label": "Normalizační"}, {"key": "ostatni", "label": "Ostatní"}],
        "jurisdiction_fallback": {"CZ": "cz", "EU": "eu"},
        "sources": {"ISO": "std", "Ministerstvo zemědělství": "cz"},
    }

    def test_explicit_entry_wins_over_the_jurisdiction_column(self):
        # Ministerstvo zemědělství has jurisdiction 'EU' in the database by mistake.
        self.assertEqual(cf.source_group_key("Ministerstvo zemědělství", "EU", self.CONFIG), "cz")

    def test_fallback_by_jurisdiction_then_other(self):
        self.assertEqual(cf.source_group_key("Nové ministerstvo", "CZ", self.CONFIG), "cz")
        self.assertEqual(cf.source_group_key("Kdosi", None, self.CONFIG), "ostatni")

    def test_groups_keep_file_order_and_drop_empty_ones(self):
        sources = [{"id": 1, "name": "ISO", "jurisdiction": None},
                   {"id": 2, "name": "Evropská komise", "jurisdiction": "EU"},
                   {"id": 3, "name": "Ministerstvo dopravy", "jurisdiction": "CZ"}]
        groups = cf.group_sources(sources, self.CONFIG)
        self.assertEqual([g["key"] for g in groups], ["cz", "eu", "std"])
        self.assertEqual([s["id"] for s in groups[0]["sources"]], [3])

    def test_committed_file_names_only_known_groups(self):
        config = cf.load_source_groups()
        keys = {g["key"] for g in config["groups"]}
        self.assertIn("ostatni", keys)
        self.assertLessEqual(set(config["sources"].values()), keys)
        self.assertLessEqual(set(config["jurisdiction_fallback"].values()), keys)
        self.assertEqual(config["sources"].get("Ministerstvo dopravy"), "cz")


class CatalogQueryTestCase(unittest.TestCase):
    """How app.py builds the catalogue query from these filters."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SECRET_KEY", "unit-test")
        from app.app import build_count_query, build_document_query
        cls.build_count_query = staticmethod(build_count_query)
        cls.build_document_query = staticmethod(build_document_query)

    BASE = {'q': '', 'type_id': '', 'eu_subtype': '', 'source_id': '', 'keyword_id': '',
            'jurisdiction': 'vse', 'synonyms': []}

    def test_grouped_list_selects_acts_through_their_variants(self):
        sql, params = self.build_document_query(self.BASE, limit=50, group_variants=True)
        self.assertIn("COALESCE(tr.to_document_id, d.id)", sql)
        self.assertIn("'TRANSLATION_OF'", sql)
        self.assertIn("WHERE d.id IN (", sql)
        self.assertEqual(params, [50])

    def test_grouped_count_counts_acts_with_the_same_filters(self):
        filters = {**self.BASE, 'q': 'vodík', 'jurisdiction': 'cz'}
        count_sql, count_params = self.build_count_query(filters, group_variants=True)
        list_sql, list_params = self.build_document_query(filters, group_variants=True)
        self.assertIn("COALESCE(tr.to_document_id, d.id)", count_sql)
        self.assertEqual(count_params, list_params)

    def test_synonyms_add_terms_and_identifiers(self):
        filters = {**self.BASE, 'q': 'RFNBO', 'synonyms': ENTRIES[2:]}
        sql, params = self.build_document_query(filters)
        self.assertIn("d.identifier IN (%s, %s)", sql)
        self.assertEqual(params, ['%RFNBO%'] * 3 + ['%nebiologického původu%'] * 2
                         + ['(EU) 2023/1184', '(EU) 2018/2001'])

    def test_subtype_and_jurisdiction(self):
        filters = {**self.BASE, 'eu_subtype': 'delegated', 'jurisdiction': 'bez-sk'}
        sql, params = self.build_document_query(filters)
        self.assertIn("AND d.eu_act_subtype = %s", sql)
        self.assertIn("d.jurisdikce <> %s", sql)
        self.assertEqual(params, ['delegated', 'SK'])

    def test_subtype_column_is_read_only_when_asked(self):
        self.assertIn("NULL AS eu_act_subtype", self.build_document_query(self.BASE)[0])
        self.assertIn("d.eu_act_subtype", self.build_document_query(self.BASE, with_subtype=True)[0])


if __name__ == "__main__":
    unittest.main()
