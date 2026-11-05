"""The adapters of stage E6 (src/tools/harvest_eu_registers.py) on recorded answers —
no network access."""
import pathlib
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import harvest_eu_registers as eu
import harvest_sources as hs
import source_registry as sr

CONTEXT = {"today": "2026-11-05", "known": set(), "documents": []}
NO_SLEEP = types.SimpleNamespace(sleep=lambda s: None)


class Response:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload

    def raise_for_status(self):
        pass


class Session:
    def __init__(self, route):
        self.route, self.calls = route, []
        self.cookies = {}

    def get(self, url, timeout=None):
        self.calls.append(("GET", url, None, None))
        self.cookies["XSRF-TOKEN"] = "token-1"
        return Response({})

    def post(self, url, params=None, json=None, headers=None, timeout=None):
        self.calls.append(("POST", url, json, headers))
        return Response(self.route(url, params or {}, json or {}))


class ComitologyTestCase(unittest.TestCase):
    def test_hydrogen_documents_without_biocides(self):
        content = [
            {"documentReference": "114884", "version": 2, "title": "Draft Commission Implementing Regulation on hydrogen refuelling",
             "committeeTitle": "Committee on alternative fuels", "creationDate": "2026-11-01T10:00:00Z", "meetingCode": "CMTD(2026)1",
             "documentType": {"label": "label.draft_implementing_act"}},
            {"documentReference": "114885", "version": 1, "title": "Postponing the expiry of the approval of hydrogen peroxide as a biocide",
             "committeeTitle": "Standing Committee on Biocidal Products", "creationDate": "2026-11-01T10:00:00Z",
             "documentType": {"label": "label.draft_implementing_act"}},
            {"documentReference": "114886", "version": 1, "title": "Agenda of the 12th meeting",
             "committeeTitle": "Hydrogen and Fuel Cells Committee", "creationDate": "2026-10-20T10:00:00Z",
             "documentType": {"label": "label.agenda"}},
            {"documentReference": "114887", "version": 1, "title": "Wine labelling", "committeeTitle": "Wines",
             "creationDate": "2026-10-20T10:00:00Z", "documentType": {"label": "label.agenda"}}]
        session = Session(lambda url, params, body: {"content": content})
        findings = eu.comitology_documents({"id": "comitology"}, session, None, CONTEXT)
        self.assertEqual(session.calls[0][2], {"reset": False})
        self.assertEqual([(f.native_id, f.signal, f.tier) for f in findings],
                         [("114884", "draft", 1), ("114886", "new_document", 2)])
        self.assertEqual(findings[0].url, "https://ec.europa.eu/transparency/comitology-register/screen/documents/114884/2/consult?lang=en")
        self.assertEqual(findings[0].key, "DRAFT-EU:comitology:114884")


class DelegatedActsTestCase(unittest.TestCase):
    def test_unpublished_acts_with_the_session_token(self):
        acts = {"hydrogen": [{"id": 3042, "delegatedActStatus": "PUBLISHED", "shortTitle": "Cross-border projects"},
                             {"id": 1054, "delegatedActStatus": "PLANNED", "completeTitle": "Delegated act on hydrogen",
                              "cCode": None, "basicAct": {"code": "dir/2018/2001"}}],
                "RFNBO": [{"id": 1054, "delegatedActStatus": "PLANNED", "completeTitle": "Delegated act on hydrogen"}],
                "non-biological origin": []}
        session = Session(lambda url, params, body: {"list": acts[body["simpleSearchName"]], "count": 0})
        with mock.patch.object(eu, "time", NO_SLEEP):
            findings = eu.delegated_acts({"id": "regdel"}, session, None, CONTEXT)
        self.assertEqual([(f.key, f.url) for f in findings],
                         [("DRAFT-EU:regdel:1054", "https://webgate.ec.europa.eu/regdel/#/delegatedActs/1054")])
        posts = [c for c in session.calls if c[0] == "POST"]
        self.assertEqual(posts[0][3], {"X-XSRF-TOKEN": "token-1"})
        self.assertEqual(len(posts), 3)


class CommissionDocumentsTestCase(unittest.TestCase):
    def test_recent_com_and_c_documents_with_hydrogen_in_the_title(self):
        def doc(ref, category, date, title):
            return {"reference": ref, "category": category, "date": f"{date}T00:00:00.000+0000", "url": f"https://x/{ref}",
                    "responsibleDepartment": "ENER", "attachments": [{"linguisticVersions": {"en": {"title": title}}}]}
        pages = {1: [doc("COM(2026)600", "COM", "2026-10-30", "Proposal for a regulation on hydrogen storage"),
                     doc("SWD(2026)777", "SWD", "2026-10-29", "Staff working document on hydrogen"),
                     doc("C(2026)500", "C", "2026-10-01", "Commission decision on hydrogen valleys"),
                     doc("COM(2026)100", "COM", "2026-09-01", "Tourism strategy")],
                 2: [doc("COM(2025)900", "COM", "2025-06-01", "Old hydrogen proposal")]}
        session = Session(lambda url, params, body: {"documents": pages.get(body["page"], [])})
        with mock.patch.object(eu, "time", NO_SLEEP):
            findings = eu.commission_documents({"id": "comdoc"}, session, None, CONTEXT)
        self.assertEqual([(f.native_id, f.signal, f.tier) for f in findings],
                         [("COM(2026)600", "draft", 2), ("C(2026)500", "new_document", 2)])
        self.assertEqual(len([c for c in session.calls if c[0] == "POST"]), 2)


class PlanTestCase(unittest.TestCase):
    def test_stage_e6_and_the_sources_now_checked_by_hand(self):
        entries, _ = sr.load()
        planned = {e["id"]: (specs, reason) for e, specs, reason in hs.plan(sr.select(entries, stage="E6"), hs.ADAPTERS)}
        self.assertEqual(sorted(i for i, (specs, _) in planned.items() if specs),
                         ["ec-comitology-register", "ec-documents-register", "ec-regdel"])
        self.assertTrue(planned["e-legislativa"][1].startswith("deferred"))
        manual = {e["id"] for e in entries if e["stage"] == "manual"}
        self.assertLessEqual({"unece-wp29", "unece-dangerous-goods", "council-public-register", "baua"}, manual)


if __name__ == "__main__":
    unittest.main()
