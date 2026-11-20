"""Integration test of the automatic triage against the TEST database (`.env.test`,
`h2regdocs_test`), never the real one: a run with --apply (the model is a fake)
proposes, rejects and defers under the technical account `automat`, writes the
AuditLog, leaves a mere recommendation where the configuration allows no action;
the automat cannot sign in; an editor confirms the automat's proposals in bulk
(each confirmation audited on its own) and reopens a rejected candidate, which a
second run then leaves alone. Fixtures (candidates `TEST-TRIAGE:…`, two editors)
are created and removed by the test; data/accepted_candidates.json is redirected."""
import argparse
import json
import os
import pathlib
import sys
import tempfile
import unittest

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
import testdb  # noqa: E402

USERS = {"triage_alice": "alice-triage-password", "triage_bob": "bob-triage-password"}
PREFIX = "TEST-TRIAGE:"


class FakeAssessor:
    """Stands in for triage.ModelAssessor: answers by the candidate's title."""
    model = "fake-model"

    def __init__(self, config, document_types, model=None, composition=None):
        self.calls = 0

    def estimate(self, payloads):
        return len(payloads), 0, 0, 0.0

    def assess(self, payload):
        self.calls += 1
        title = payload["kandidat"]["nazev"]
        accept = "tlakov" in title
        return {"reasoning": "Testovací zdůvodnění.", "recommendation": "accept" if accept else "reject",
                "category": "v_rozsahu" if accept else "mimo_rozsah", "scope_areas": [7] if accept else [],
                "document_type": "Zákon" if accept else None, "puvodce": "Testovací původce triáže" if accept else None,
                "official_title": None, "confidence": 0.99, "token_confidence": 0.99}


class TriageDatabaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env_test = testdb.find_env_file(".env.test")
        cls._saved_environ = dict(os.environ)
        load_dotenv(env_test, override=True)
        if os.environ.get("DB_NAME") != "h2regdocs_test":
            raise unittest.SkipTest(".env.test does not point at h2regdocs_test — refusing to guess")
        from app.app import app
        import candidates_admin
        import candidates as cd
        import triage
        import triage_candidates
        cls.cd, cls.triage, cls.triage_candidates = cd, triage, triage_candidates
        cls.candidates_admin = candidates_admin
        cls.tmp = tempfile.TemporaryDirectory()
        cls._saved_path = candidates_admin.ACCEPTED_PATH
        candidates_admin.ACCEPTED_PATH = pathlib.Path(cls.tmp.name) / "accepted.json"
        cls.app = app
        import pymysql
        cls.conn = pymysql.connect(host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
                                   user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
                                   database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor)
        cls.conn.autocommit(True)
        with cls.conn.cursor() as cur:
            cd.ensure_schema(cur)
        cls.cleanup()
        with cls.conn.cursor() as cur:
            for username, password in USERS.items():
                cur.execute("INSERT INTO User (username, name, email, password_hash) VALUES (%s, %s, %s, %s)",
                            (username, username.replace("_", " ").title(), f"{username}@example.test",
                             generate_password_hash(password)))

    @classmethod
    def cleanup(cls):
        with cls.conn.cursor() as cur:
            cur.execute("SELECT id, document_id FROM DocumentCandidate WHERE candidate_key LIKE %s", (PREFIX + "%",))
            rows = cur.fetchall()
            for row in rows:
                cur.execute("DELETE FROM AuditLog WHERE table_name = 'DocumentCandidate' AND record_id = %s", (row["id"],))
                if row["document_id"]:
                    for table in ("DocumentKeyword", "DocumentVersion"):
                        cur.execute(f"DELETE FROM {table} WHERE document_id = %s", (row["document_id"],))
                    cur.execute("DELETE FROM AuditLog WHERE table_name = 'Document' AND record_id = %s",
                                (row["document_id"],))
            cur.execute("DELETE FROM DocumentCandidate WHERE candidate_key LIKE %s", (PREFIX + "%",))
            for row in rows:
                if row["document_id"]:
                    cur.execute("DELETE FROM Document WHERE id = %s", (row["document_id"],))
            cur.execute("DELETE FROM DocumentSource WHERE name IN ('Testovací původce triáže', 'Český plynárenský svaz (ČPS)') "
                        "AND id NOT IN (SELECT source_id FROM Document WHERE source_id IS NOT NULL)")
            cur.execute("DELETE FROM AuditLog WHERE changed_by_user_id IN (SELECT id FROM User WHERE username IN (%s, %s))",
                        tuple(USERS))
            cur.execute("DELETE FROM User WHERE username IN (%s, %s)", tuple(USERS))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn"):
            cls.cleanup()
            cls.conn.close()
        if hasattr(cls, "_saved_path"):
            cls.candidates_admin.ACCEPTED_PATH = cls._saved_path
            cls.tmp.cleanup()
        if hasattr(cls, "_saved_environ"):
            os.environ.clear()
            os.environ.update(cls._saved_environ)

    def insert(self, key, source, title, **fields):
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO DocumentCandidate (candidate_key, source, `signal`, designation, title,
                               document_type, url, language, jurisdikce, validity_status, evidence_json, cited_by)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 2)""",
                        (PREFIX + key, source, fields.get("signal"), fields.get("designation"), title,
                         fields.get("document_type"), fields.get("url", "https://example.test/" + key),
                         fields.get("language"), fields.get("jurisdikce"), fields.get("validity_status"),
                         json.dumps(fields.get("evidence", {}))))
            return cur.lastrowid

    def candidate(self, candidate_id):
        with self.conn.cursor() as cur:
            cur.execute("""SELECT c.*, pu.username AS proposer, du.username AS decider FROM DocumentCandidate c
                           LEFT JOIN User pu ON pu.id = c.proposed_by_user_id
                           LEFT JOIN User du ON du.id = c.decided_by_user_id WHERE c.id = %s""", (candidate_id,))
            return cur.fetchone()

    def run_triage(self, ids):
        args = argparse.Namespace(apply=True, ids=ids, rule=None, limit=None, sample=None, seed=1, rules_only=False,
                                  model=None, max_usd=None)
        config = self.triage.load_config()
        lines = []
        import pymysql
        conn = pymysql.connect(host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
                               user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
                               database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor)
        try:
            return self.triage_candidates.run(conn, "h2regdocs_test", args, config, FakeAssessor, lines.append)
        finally:
            conn.close()

    def client_for(self, username):
        client = self.app.test_client()
        client.post("/admin/login", data={"username": username, "password": USERS[username]})
        return client

    def test_triage_then_editors(self):
        tpg = self.insert("TPG 304 03", "cps-tpg", "TPG 304 03 Plnicí stanice stlačeného vodíku pro mobilní zařízení",
                          designation="TPG 304 03", document_type="Norma", signal="new_document")
        repealed = self.insert("CZ:9001/2099", "mpo", "Vyhláška zrušená", designation="9001/2099 Sb.",
                               document_type="Vyhláška", language="CS", jurisdikce="CZ", validity_status="zrušený")
        news = self.insert("news", "acer", "ACER news item", url="https://www.acer.europa.eu/news/test-triage",
                           signal="new_document")
        accepted = self.insert("CZ:9002/2099", "citation", "Zákon o tlakových zařízeních pro zkoušky",
                               designation="9002/2099 Sb.", document_type="Nezařazeno", language="CS",
                               jurisdikce="CZ", validity_status="účinný")
        declined = self.insert("CZ:9003/2099", "citation", "Zákon o myslivosti pro zkoušky", designation="9003/2099 Sb.",
                               document_type="Zákon", language="CS", jurisdikce="CZ", validity_status="účinný")
        ids = [tpg, repealed, news, accepted, declined]
        results = self.run_triage(ids)
        self.assertEqual({c["id"]: taken for c, _, taken in results},
                         {tpg: "propose", repealed: "reject", news: "defer", accepted: "propose", declined: "recommend"})

        c = self.candidate(tpg)
        self.assertEqual((c["status"], c["proposer"], c["document_type"], c["puvodce"], c["scope_areas"], c["title"]),
                         ("proposed", "automat", "Norma", "Český plynárenský svaz (ČPS)", "4",
                          "Plnicí stanice stlačeného vodíku pro mobilní zařízení"))
        self.assertEqual((self.candidate(repealed)["status"], self.candidate(repealed)["decider"]), ("rejected", "automat"))
        self.assertTrue(self.candidate(repealed)["decision_note"].startswith("Automat (R2-zruseny)"))
        self.assertEqual(self.candidate(news)["status"], "deferred")
        c = self.candidate(accepted)
        self.assertEqual((c["status"], c["document_type"], c["triage_recommendation"]), ("proposed", "Zákon", "accept"))
        c = self.candidate(declined)
        self.assertEqual((c["status"], c["triage_recommendation"], float(c["triage_confidence"])), ("new", "reject", 0.99))
        self.assertEqual(json.loads(c["triage_json"])["model"]["category"], "mimo_rozsah")

        with self.conn.cursor() as cur:
            cur.execute("""SELECT a.action, a.new_value_json FROM AuditLog a JOIN User u ON u.id = a.changed_by_user_id
                           WHERE u.username = 'automat' AND a.table_name = 'DocumentCandidate' AND a.record_id IN
                           (%s, %s, %s, %s, %s) ORDER BY a.id""", ids)
            trail = cur.fetchall()
            cur.execute("SELECT is_active, password_hash, name FROM User WHERE username = 'automat'")
            automat = cur.fetchone()
        self.assertEqual(sorted(t["action"] for t in trail), ["DEFER", "PROPOSE", "PROPOSE", "REJECT"])
        self.assertTrue(all(json.loads(t["new_value_json"])["automat"] for t in trail))
        self.assertEqual((automat["is_active"], automat["password_hash"], automat["name"]),
                         (0, "!", "Automatický navrhovatel"))

        # the automat never signs in, whatever password
        for password in ("!", "", "automat"):
            response = self.app.test_client().post("/admin/login", data={"username": "automat", "password": password})
            self.assertIn("Neplatné přihlašovací jméno", response.get_data(as_text=True))

        alice = self.client_for("triage_alice")
        page = alice.get("/admin/candidates?automat=navrhy&q=").get_data(as_text=True)
        self.assertIn("Plnicí stanice stlačeného vodíku", page)
        self.assertIn("automat-badge", page)
        detail = alice.get(f"/admin/candidates/{declined}").get_data(as_text=True)
        self.assertIn("Doporučení automatu", detail)
        self.assertIn("Testovací zdůvodnění.", detail)

        # bulk: a rejection needs a reason; the confirmation creates both documents, each audited on its own
        alice.post("/admin/candidates/bulk", data={"action": "reject", "ids": [str(declined)]})
        self.assertEqual(self.candidate(declined)["status"], "new")
        alice.post("/admin/candidates/bulk", data={"action": "confirm", "ids": [str(tpg), str(accepted), str(declined)]})
        for candidate_id in (tpg, accepted):
            c = self.candidate(candidate_id)
            self.assertEqual(c["status"], "accepted")
            self.assertIsNotNone(c["document_id"])
        self.assertEqual(self.candidate(declined)["status"], "new")  # not proposed: skipped
        with self.conn.cursor() as cur:
            cur.execute("""SELECT record_id, new_value_json FROM AuditLog WHERE action = 'CONFIRM'
                           AND table_name = 'DocumentCandidate' AND record_id IN (%s, %s)""", (tpg, accepted))
            confirms = cur.fetchall()
        self.assertEqual(sorted(r["record_id"] for r in confirms), sorted([tpg, accepted]))
        self.assertTrue(all(json.loads(r["new_value_json"])["bulk"] for r in confirms))
        accepted_json = json.loads(self.candidates_admin.ACCEPTED_PATH.read_text(encoding="utf-8"))
        self.assertEqual(accepted_json[PREFIX + "TPG 304 03"]["proposed_by"], "automat")

        # an editor reopens what the automat rejected; the next run leaves it to the editors
        alice.post(f"/admin/candidates/{repealed}/reopen", data={"decision_note": "chci posoudit sám"})
        self.assertEqual(self.candidate(repealed)["status"], "new")
        results = self.run_triage([repealed, declined])
        self.assertEqual({c["id"]: taken for c, _, taken in results}, {repealed: "recommend", declined: "recommend"})
        self.assertEqual(self.candidate(repealed)["status"], "new")

        # bulk defer with a note
        alice.post("/admin/candidates/bulk", data={"action": "defer", "ids": [str(declined)], "decision_note": "později"})
        c = self.candidate(declined)
        self.assertEqual((c["status"], c["decider"], c["decision_note"]), ("deferred", "triage_alice", "později"))


if __name__ == "__main__":
    unittest.main()
