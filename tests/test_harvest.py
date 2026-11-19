import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import candidates as cd
import harvest


class FindingTestCase(unittest.TestCase):
    def test_a_finding_with_a_key_keeps_it(self):
        finding = harvest.Finding("eurlex-cellar", "new_document", "Nařízení", key="EU:2024/1789",
                                  designation="(EU) 2024/1789")
        self.assertEqual(finding.candidate_key(), "EU:2024/1789")
        self.assertNotIn("needs_key", finding.as_evidence("2026-10-28"))

    def test_a_finding_without_a_key_gets_one_of_its_own_and_a_flag(self):
        finding = harvest.Finding("veklep-odok", "draft", "Návrh zákona", native_id="KORNXYZ")
        self.assertEqual(finding.candidate_key(), "veklep-odok:KORNXYZ")
        by_url = harvest.Finding("ep-oeil", "draft", "Procedure", url="https://oeil.test/1")
        self.assertEqual(by_url.candidate_key(), by_url.candidate_key())
        self.assertTrue(by_url.candidate_key().startswith("ep-oeil:"))
        self.assertTrue(by_url.as_evidence("2026-10-28")["needs_key"])

    def test_the_type_of_a_draft_or_an_amendment_is_read_from_its_title(self):
        # titles seen in the dress rehearsal of 2026-11-05 (doc/DATA_SOURCES.md odstavec 8.16)
        cases = [("draft", "CZ", "Vládní návrh zákona, kterým se mění zákon č. 73/2012 Sb., o látkách", "Zákon"),
                 ("draft", "CZ", "Návrh poslanců Petra Hladíka a dalších na vydání zákona, kterým se mění", "Zákon"),
                 ("draft", "CZ", "Senátní návrh zákona, kterým se mění zákon č. 13/1997 Sb.", "Zákon"),
                 ("draft", "CZ", "Vyhláška, kterou se mění vyhláška č. 343/2014 Sb., k provedení zákona", "Vyhláška"),
                 ("draft", "CZ", "Nařízení vlády, kterým se mění nařízení vlády č. 1/2020 Sb.", "Nařízení vlády"),
                 ("amendment", "CZ", "Zákon, kterým se mění zákon č. 311/2006 Sb., o pohonných hmotách", "Zákon"),
                 ("draft", "EU", "Změna směrnic (EU) 2018/2001, (EU) 2019/944 a (EU) 2024/1788", "Směrnice EU"),
                 ("draft", "EU", "Změna nařízení Evropského parlamentu a Rady 2008/98/ES, 2010/75/EU", "Nařízení EU"),
                 ("draft", "EU", "Commission Delegated Directive introducing lifecycle greenhouse gas", "Směrnice EU"),
                 ("draft", "EU", "COMMISSION REGULATION (EU) …/… amending Annex XVII to Regulation", "Nařízení EU"),
                 ("draft", "EU", "Hydrogen strategy", None),
                 ("draft", "EU", "Zřízení Dočasného fondu pro dekarbonizaci", None),
                 ("new_document", "CZ", "Zákon o vodíku schválila vláda", None),
                 ("draft", None, "Directive on something", None)]
        for signal, jurisdikce, title, expected in cases:
            finding = harvest.Finding("src", signal, title, jurisdikce=jurisdikce)
            self.assertEqual(finding.as_candidate()["document_type"], expected, title)
        given = harvest.Finding("src", "draft", "Vyhláška, kterou", jurisdikce="CZ", document_type="Metodika")
        self.assertEqual(given.as_candidate()["document_type"], "Metodika")

    def test_search_terms(self):
        self.assertTrue(harvest.matches("Návrh vyhlášky o plnicích stanicích vodíku"))
        self.assertTrue(harvest.matches("Regulation on hydrogen and decarbonised gas markets"))
        self.assertTrue(harvest.matches("Verordnung über Wasserstofftankstellen"))
        self.assertFalse(harvest.matches("Novela zákona o tlakových zařízeních"))
        self.assertTrue(harvest.matches("Novela nařízení vlády o tlaková zařízení", broader=True))
        self.assertFalse(harvest.matches("Zpráva o hospodaření úřadu", broader=True))
        self.assertFalse(harvest.matches("dehydrogenace"))


class Cursor:
    """A fake DictCursor: one stored candidate row per key, and the documents."""

    def __init__(self, rows=None, documents=()):
        self.rows, self.documents, self.result, self.writes = dict(rows or {}), list(documents), None, []

    def execute(self, sql, params=None):
        sql = " ".join(sql.split())
        if sql.startswith("SELECT id, identifier, title, url FROM Document"):
            self.result = [{"id": n, "identifier": d[0], "title": d[1], "url": d[2] if len(d) > 2 else None}
                           for n, d in enumerate(self.documents, 1)]
        elif sql.startswith("SELECT id, status, evidence_json FROM DocumentCandidate"):
            self.result = self.rows.get(params[0])
        else:
            self.writes.append((sql.split()[0], params))
            if sql.startswith("INSERT"):
                self.rows[params[0]] = {"id": len(self.rows) + 1, "status": "new", "evidence_json": params[9]}
            elif sql.startswith("UPDATE"):
                for row in self.rows.values():
                    if row["id"] == params[-1]:
                        row["evidence_json"] = params[0]

    def fetchone(self):
        return self.result

    def fetchall(self):
        return self.result


class WriteFindingsTestCase(unittest.TestCase):
    def test_findings_go_to_the_queue_unless_the_database_has_the_document(self):
        cursor = Cursor(documents=[("(EU) 2024/1789", "Nařízení (EU) 2024/1789 o trzích s vodíkem")])
        known = harvest.known_keys(cursor)
        self.assertIn("EU:2024/1789", known)
        self.assertEqual(harvest.known_keys([(1, None, "Studie", "https://hytep.test/a.pdf")]),
                         {"url:https://hytep.test/a.pdf"})
        findings = [harvest.Finding("eurlex-cellar", "new_document", "known", key="EU:2024/1789"),
                    harvest.Finding("veklep-odok", "draft", "Návrh zákona o vodíku", native_id="A1"),
                    harvest.Finding("eurlex-cellar", "state_change", "zrušeno", key="EU:2003/87"),
                    harvest.Finding("hytep", "context", "zpráva")]
        outcome = harvest.write_findings(cursor, findings, known, "2026-10-28T10:00:00+00:00")
        self.assertEqual(dict(outcome), {"known": 1, "inserted": 1, "state_change": 1, "not_queued": 1})
        insert = [p for kind, p in cursor.writes if kind == "INSERT"][0]
        self.assertEqual(insert[:3], ("veklep-odok:A1", "veklep-odok", "draft"))

    def test_a_second_source_adds_its_finding_and_keeps_the_first(self):
        cursor = Cursor()
        first = harvest.Finding("veklep-odok", "draft", "Návrh", key="CZ:1/2027")
        harvest.write_findings(cursor, [first], set(), "2026-10-01T00:00:00+00:00")
        second = harvest.Finding("psp-snemovni-tisky", "draft", "Sněmovní tisk 1", key="CZ:1/2027")
        self.assertEqual(dict(harvest.write_findings(cursor, [second], set(), "2026-10-28T00:00:00+00:00")),
                         {"updated": 1})
        harvest.write_findings(cursor, [first], set(), "2026-10-29T00:00:00+00:00")
        findings = json.loads(cursor.rows["CZ:1/2027"]["evidence_json"])["findings"]
        self.assertEqual(sorted(findings), ["psp-snemovni-tisky", "veklep-odok"])
        self.assertEqual(findings["veklep-odok"]["first_seen"], "2026-10-01T00:00:00+00:00")
        self.assertEqual(findings["veklep-odok"]["seen"], "2026-10-29T00:00:00+00:00")

    def test_a_decided_candidate_is_not_touched(self):
        cursor = Cursor({"CZ:1/2027": {"id": 1, "status": "rejected", "evidence_json": "{}"}})
        finding = harvest.Finding("veklep-odok", "draft", "Návrh", key="CZ:1/2027")
        self.assertEqual(dict(harvest.write_findings(cursor, [finding], set(), "x")), {"kept": 1})
        self.assertEqual(cursor.writes, [])


class CheckUpsertKeepsFindingsTestCase(unittest.TestCase):
    def test_a_refreshed_citation_keeps_the_findings_of_sources(self):
        stored = {"findings": {"veklep-odok": {"source": "veklep-odok", "seen": "x"}}, "citing_ids": [1]}
        cursor = Cursor({"CZ:1/2027": {"id": 1, "status": "new", "evidence_json": json.dumps(stored)}})
        cd.upsert(cursor, {"candidate_key": "CZ:1/2027", "source": "citation", "evidence": {"citing_ids": [1, 2]},
                           "cited_by": 2})
        evidence = json.loads(cursor.writes[-1][1][0])
        self.assertEqual(evidence["citing_ids"], [1, 2])
        self.assertIn("veklep-odok", evidence["findings"])


class LogTestCase(unittest.TestCase):
    def test_runs_are_appended_and_the_last_successful_applied_one_is_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "log.jsonl"
            self.assertEqual(harvest.read_log(path), [])
            harvest.log_run({"kind": "harvest", "source": "a", "applied": True, "findings": 0}, path)
            harvest.log_run({"kind": "harvest", "source": "a", "applied": False, "findings": 3}, path)
            harvest.log_run({"kind": "harvest", "source": "a", "applied": True, "error": "boom"}, path)
            harvest.log_run({"kind": "availability", "source": "a", "applied": True}, path)
            records = harvest.read_log(path)
            self.assertEqual(len(records), 4)
            self.assertTrue(all("at" in r for r in records))
            last = harvest.last_runs(records)
            self.assertEqual(last["a"]["findings"], 0)
            self.assertEqual(harvest.last_runs(records, successful=False)["a"]["error"], "boom")


if __name__ == "__main__":
    unittest.main()
