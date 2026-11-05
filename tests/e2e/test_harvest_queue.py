"""Browser scenario: the chain from monitored sources to the database — findings
written by harvest.write_findings() (as a run with --apply writes them), the
candidate queue with its filters (tier, source, family), the detail of a draft
found by two sources with the document it amends, and the acceptance by two
editors, after which the draft exists as a document in the state „připravovaný“
with the relation „novelizuje“.

The findings are recorded, not harvested: the scenario needs no network. They
cover what a real run produces — a draft act from the Chamber of Deputies seen
again in the Senate (one candidate, two findings), a standard in tier 2, a new
act with an amendment attached, an excluded finding and a finding of a document
the database already has (neither reaches the queue).

Fixtures (two editors, candidates with the keys in KEYS) are created in, and
removed from, the TEST database; data/accepted_candidates.json is restored."""
import pathlib
import re
import sys
import tempfile

from werkzeug.security import generate_password_hash

from browser_case import BrowserTestCase, database_connection

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src" / "tools"))
import candidates  # noqa: E402
import harvest  # noqa: E402
from harvest import Finding  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
ACCEPTED = REPO_ROOT / "data" / "accepted_candidates.json"
SEEN = "2026-11-05T10:00:00+00:00"
DRAFT_KEY = "DRAFT-CZ:psp:E2ETEST-9999"
DRAFT_TITLE = "E2ETEST Vládní návrh zákona, kterým se mění zákon o vodíkových plnicích stanicích"
NORM_KEY = "NORM:ČSN E2ETEST 65 9999"
NORM_TITLE = "ČSN E2ETEST 65 9999 Vodíkové technologie — plnicí stanice (návrh normy)"
ACT_KEY = "CZ:9901/2099"
ACT_TITLE = "E2ETEST Vyhláška o technických požadavcích na vodíkové zásobníky"
KEYS = (DRAFT_KEY, NORM_KEY, ACT_KEY)
PASSWORDS = {"e2e_harv_alice": "alice-harv-e2e", "e2e_harv_bob": "bob-harv-e2e"}


def recorded_findings(amended_id, known_key):
    """What the adapters of a run return (harvest_drafts, harvest_standards,
    harvest_adapters), shortened to the fields the queue reads."""
    draft = dict(signal="draft", title=DRAFT_TITLE, key=DRAFT_KEY, document_type="Zákon", language="CS",
                 jurisdikce="CZ", extra={"amends_ids": [amended_id]})
    return [
        Finding(source="psp-snemovni-tisky", url="https://example.test/psp/tisk/9999", date="2026-10-21",
                excerpt="sněmovní tisk 9999, 1. čtení", **draft),
        Finding(source="senat-tisky", url="https://example.test/senat/tisk/999", date="2026-11-02",
                excerpt="senátní tisk 999, přikázán výborům", **draft),
        Finding(source="vestnik-unmz", signal="new_document", title=NORM_TITLE, key=NORM_KEY,
                designation="ČSN E2ETEST 65 9999", document_type="Norma", language="CS", jurisdikce="CZ",
                url="https://example.test/unmz/vestnik/11-2026", date="2026-11-01", tier=2,
                excerpt="Věstník ÚNMZ 11/2026, návrhy norem k připomínkám"),
        Finding(source="esbirka-lod", signal="new_document", title=ACT_TITLE, key=ACT_KEY,
                designation="9901/2099 Sb.", document_type="Vyhláška", language="CS", jurisdikce="CZ",
                url="https://example.test/esbirka/9901-2099", tier=1, occurrences=7,
                excerpt="vodíkové zásobníky (poslední znění, 7 míst v textu)",
                extra={"amended_by": [{"key": "CZ:9902/2099", "title": "E2ETEST novela vyhlášky"}]}),
        Finding(source="esbirka-lod", signal="excluded", title="E2ETEST Sazebník správních poplatků",
                key="CZ:9903/2099", extra={"reason": "sazebník"}),
        Finding(source="esbirka-lod", signal="new_document", title="už je v databázi", key=known_key),
    ]


class HarvestQueueTestCase(BrowserTestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved_accepted = ACCEPTED.read_text(encoding="utf-8") if ACCEPTED.exists() else None
        cls.db = database_connection()
        with cls.db.cursor() as cur:
            candidates.ensure_schema(cur)
        cls.cleanup()
        super().setUpClass()
        with cls.db.cursor() as cur:
            for username in PASSWORDS:
                cur.execute("INSERT INTO User (username, name, email, password_hash) VALUES (%s, %s, %s, %s)",
                            (username, username.replace("e2e_harv_", "").title() + " E2E", f"{username}@example.test",
                             generate_password_hash(PASSWORDS[username])))
            cur.execute("""SELECT id, identifier, title FROM Document
                           WHERE jurisdikce = 'CZ' AND identifier LIKE '%%/%% Sb.' ORDER BY id LIMIT 1""")
            cls.amended = cur.fetchone()
            known = harvest.known_keys(cur)
            known_key = next(k for k in sorted(known) if k.startswith("CZ:"))
            cls.outcome = harvest.write_findings(cur, recorded_findings(cls.amended["id"], known_key), known, SEEN)
        with tempfile.TemporaryDirectory() as folder:
            cls.excluded = harvest.record_excluded(recorded_findings(0, ""), SEEN, pathlib.Path(folder) / "x.json")

    @classmethod
    def cleanup(cls):
        marks = ",".join(["%s"] * len(KEYS))
        with cls.db.cursor() as cur:
            cur.execute(f"SELECT id, document_id FROM DocumentCandidate WHERE candidate_key IN ({marks})", KEYS)
            rows = cur.fetchall()
            for row in rows:
                cur.execute("DELETE FROM AuditLog WHERE table_name = 'DocumentCandidate' AND record_id = %s", (row["id"],))
                if row["document_id"]:
                    for table in ("DocumentKeyword", "DocumentVersion"):
                        cur.execute(f"DELETE FROM {table} WHERE document_id = %s", (row["document_id"],))
                    cur.execute("DELETE FROM document_relation WHERE from_document_id = %s", (row["document_id"],))
                    cur.execute("DELETE FROM AuditLog WHERE table_name = 'Document' AND record_id = %s", (row["document_id"],))
            cur.execute(f"DELETE FROM DocumentCandidate WHERE candidate_key IN ({marks})", KEYS)
            for row in rows:
                if row["document_id"]:
                    cur.execute("DELETE FROM Document WHERE id = %s", (row["document_id"],))
            cur.execute("DELETE FROM User WHERE username IN (%s, %s)", tuple(PASSWORDS))

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "db", None):
            cls.cleanup()
            cls.db.close()
        if cls.saved_accepted is None:
            ACCEPTED.unlink(missing_ok=True)
        else:
            ACCEPTED.write_text(cls.saved_accepted, encoding="utf-8")
        super().tearDownClass()

    def login(self, page, username):
        self.goto(page, "/admin/login")
        page.fill("#username", username)
        page.fill("#password", PASSWORDS[username])
        page.click("button[type=submit]")

    def row(self, page, title):
        return page.locator("table.candidate-table tbody tr", has_text=title)

    def filter(self, page, **values):
        """Sets the filter form of the list as an editor would and submits it."""
        for name, value in values.items():
            if name == "q":
                page.fill("form.candidate-filters input[name=q]", value)
            else:
                page.select_option(f"form.candidate-filters select[name={name}]", value)
        page.click("form.candidate-filters button[type=submit]")
        page.wait_for_load_state("load")

    def test_1_findings_reach_the_queue(self):
        # psp + senat: one candidate; the standard and the act: one each; the excluded and the known: none.
        self.assertEqual(self.outcome["inserted"], 3, self.outcome)
        self.assertEqual(self.outcome["updated"], 1, self.outcome)
        self.assertEqual(self.outcome["excluded"], 1, self.outcome)
        self.assertEqual(self.outcome["known"], 1, self.outcome)
        self.assertEqual(self.excluded, 1)

    def test_2_queue_filters_detail_and_acceptance(self):
        alice = self.new_page()
        self.login(alice, "e2e_harv_alice")
        self.goto(alice, "/admin/candidates?q=E2ETEST")
        # Tier 1 by default: the draft and the act, not the standard.
        self.assertEqual(self.row(alice, DRAFT_TITLE).count(), 1)
        self.assertEqual(self.row(alice, ACT_TITLE).count(), 1)
        self.assertEqual(self.row(alice, NORM_TITLE).count(), 0)
        self.shot(alice, "01-queue-tier-1")
        self.filter(alice, pasmo="2")
        self.assertEqual(self.row(alice, NORM_TITLE).count(), 1)
        self.assertTrue(self.row(alice, NORM_TITLE).get_by_text("nepřímý vztah").is_visible())
        self.assertEqual(self.row(alice, DRAFT_TITLE).count(), 0)
        self.shot(alice, "02-queue-tier-2")
        self.filter(alice, pasmo="all", zdroj="psp-snemovni-tisky")
        self.assertEqual(self.row(alice, DRAFT_TITLE).count(), 1)
        self.assertEqual(self.row(alice, ACT_TITLE).count(), 0)
        self.filter(alice, zdroj="", skupina="CZ")  # drafts `DRAFT-CZ:` belong to the Czech family
        self.assertEqual(self.row(alice, DRAFT_TITLE).count(), 1)
        self.assertEqual(self.row(alice, ACT_TITLE).count(), 1)
        self.assertEqual(self.row(alice, NORM_TITLE).count(), 0)
        self.filter(alice, skupina="EU")
        self.assertEqual(self.row(alice, DRAFT_TITLE).count(), 0)
        self.shot(alice, "03-queue-family-filter")

        # The act carries the amendment found with it.
        self.goto(alice, "/admin/candidates?q=E2ETEST")
        self.row(alice, ACT_TITLE).get_by_role("link", name="Otevřít").click()
        self.assertTrue(alice.get_by_text("Zmínku vložily nebo mění novely").is_visible())
        self.assertTrue(alice.get_by_text("9902/2099 Sb.").is_visible())
        self.shot(alice, "04-act-with-amendment")

        # The draft: two findings, the amended document of the database, proposed by Alice.
        self.goto(alice, "/admin/candidates?q=E2ETEST")
        self.row(alice, DRAFT_TITLE).get_by_role("link", name="Otevřít").click()
        self.assertTrue(alice.get_by_text("Nálezy ve sledovaných zdrojích (2)").is_visible())
        self.assertTrue(alice.get_by_text("Mění tyto dokumenty databáze").is_visible())
        self.assertTrue(alice.locator("ul.doc-relations a", has_text=self.amended["identifier"]).first.is_visible())
        alice.select_option("#scope_area", "4")
        self.shot(alice, "05-draft-detail")
        alice.click("button:has-text('Navrhnout přijetí')")
        alice.wait_for_url(re.compile(r"/admin/candidates$"))

        # Bob confirms: the document exists as a draft amending the database document.
        bob = self.new_page()
        self.login(bob, "e2e_harv_bob")
        self.goto(bob, "/admin/candidates?q=E2ETEST&stav=proposed&pasmo=all")
        self.row(bob, DRAFT_TITLE).get_by_role("link", name="Otevřít").click()
        bob.click("button:has-text('Potvrdit přijetí')")
        self.assertTrue(bob.get_by_text("Kandidát přijat a dokument založen").is_visible())
        bob.get_by_role("link", name="založen v databázi").click()
        self.assertTrue(bob.get_by_text("připravovaný").first.is_visible())
        relation = bob.locator("ul.doc-relations li", has_text="novelizuje")
        self.assertEqual(relation.count(), 1)
        self.assertIn(self.amended["identifier"], relation.inner_text())
        self.shot(bob, "06-draft-document")

        with self.db.cursor() as cur:
            cur.execute("""SELECT d.id, v.lifecycle_state FROM DocumentCandidate c JOIN Document d ON d.id = c.document_id
                           JOIN DocumentVersion v ON v.document_id = d.id WHERE c.candidate_key = %s""", (DRAFT_KEY,))
            doc = cur.fetchone()
            self.assertEqual(doc["lifecycle_state"], "draft")
            cur.execute("SELECT to_document_id FROM document_relation WHERE from_document_id = %s "
                        "AND relation_type = 'AMENDS'", (doc["id"],))
            self.assertEqual([r["to_document_id"] for r in cur.fetchall()], [self.amended["id"]])
