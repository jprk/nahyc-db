"""Builds the corrections of the record check of 2026-11-23 (doc/KONTROLA_ZAZNAMU.md,
odstavec 7) and adds them to data/manual_corrections.json.

The user decided (2026-11-23): fix the 47 errors — every document verified in its
source, the description taken from the ISO or ČAS annotation or from the text, an
uncertain description removed; merge the duplicates; turn the drafts ISO has
published into the published standard; take the 28 EU acts out of scope out of the
catalogue. Principle 7 of doc/PROVOZ.md applies: titles come from a register, never
from a model.

What it writes, in this order (apply_manual_corrections.py applies the file in order,
and a merge needs its survivor under the new identifier first):

1. ISO standards (ISO Open Data, iso_open_data.py): every document whose own identifier
   is an ISO designation and that is a draft ISO has moved on, a duplicate of another
   document of the same ISO project, or a document with an error, gets the current
   designation (published: without year; in progress: with its stage, "ISO/DIS 19885-2"),
   the ISO title and the ISO abstract as its description; it keeps its slug. The other
   documents of the same project are merged into it.
2. The decisions about single documents (`MANUAL`), each verified in its source (the
   reason says where).
3. Descriptions without a source that contradict the document are removed (`NO_SOURCE`):
   the record is flagged as missing a description.
4. Duplicates outside ISO (`MERGES`) and the EU acts out of scope (`OUT_OF_SCOPE`).

    .venv/bin/python src/tools/plan_record_fixes.py            # prints the plan
    .venv/bin/python src/tools/plan_record_fixes.py --write    # adds it to data/manual_corrections.json

Reads the live database (or `--env-file`) and never writes it.
"""
import argparse
import collections
import json
import pathlib
import re
import sys

import check_records as cr
import document_terms as dterms
import fetch_ics
import iso_open_data
from build_unified_db import MANUAL_CORRECTIONS_PATH
import state_paths

TODAY = "2026-11-23"
BY = "jprk"
DOC = "doc/KONTROLA_ZAZNAMU.md"
STAGE_PREFIX = re.compile(r"^ISO/(AWI|PWI|NP|WD|CD|DIS|FDIS|PRF|DTR|DTS)\b")
# documents with an error (doc/KONTROLA_ZAZNAMU.md, příloha A) that the ISO step corrects
ISO_ERRORS = {562, 573, 575, 576, 582, 587, 588, 589, 590, 594, 600, 616, 670, 1167, 1187, 1188, 1204}
# ISO standards whose description the ISO abstract replaces although they are adoptions (ČSN, STN)
ISO_DESCRIPTION = {35: "ISO 13850", 430: "ISO 14001"}
# the ISO project a document stands for when the lookup by its designation finds an abandoned one:
# ISO 19884 (stage 50.98, abandoned) continues as ISO/FDIS 19884-1 with the same title
ISO_OVERRIDE = {573: "ISO/FDIS 19884-1"}


def abandoned(record):
    """A project ISO abandoned (substage 98: "ISO/CD 17268-3" 30.98, "ISO/FDIS 19884" 50.98)."""
    return (record.get("currentStage") or 0) % 100 == 98

SK_2013_732 = ("Vykonávacie rozhodnutie Komisie z 9. decembra 2013, ktorým sa podľa smernice Európskeho parlamentu "
               "a Rady 2010/75/EÚ o priemyselných emisiách stanovujú závery o najlepších dostupných technikách (BAT) "
               "na výrobu chlóru a lúhov [oznámené pod číslom C(2013) 8589] (Text s významom pre EHP)")

MANUAL = {
    "2010/75/EU": ({"znacka": "(EU) 2013/732 [SK]", "nazev_cz": SK_2013_732, "nazev_autoritativni": SK_2013_732,
                    "zdroj_autoritativni_url": "https://eur-lex.europa.eu/legal-content/SK/ALL/?uri=CELEX:32013D0732",
                    "odkaz_hlavni": "https://eur-lex.europa.eu/legal-content/SK/TXT/?uri=CELEX:32013D0732",
                    "jurisdikce": "EU", "anotace_poznamka": "", "popis_autoritativni": ""},
                   "Rešerše Sinay uvádí pod číslem 2010/75/EU slovenský název prováděcího rozhodnutí o závěrech BAT pro "
                   "výrobu chloru a alkálií, tj. (EU) 2013/732 (české znění je dokument (EU) 2013/732); autoritativní "
                   "název ze Slov-Lexu (oznámení o zdravotní způsobilosti posádek plavidel) patřil jinému předpisu se "
                   "stejným číslem. Úřední slovenský název z Cellaru (CELEX 32013D0732)."),
    "STN EN ISO 11114-1/Zmena": ({"nazev_cz": "Prepravné fľaše na plyny. Kompatibilita fľašových a ventilových "
                                              "materiálov s plynovým obsahom. Časť 1: Kovové materiály "
                                              "(ISO 11114-1: 2020/Amd 1: 2023)", "platnost": "od 03/2024"},
                                 "Název byl ve zdroji (PDF rešerše Sinay) rozdělen do dvou řádků; druhý řádek "
                                 "(„A1/ - 2024.03“) vznikl jako samostatný záznam a slučuje se sem."),
    "prEN IEC 63341-2": ({"nazev_cz": "Dráhové aplikácie. Dráhové vozidlá. Systémy palivových článkov na pohon. Časť 2: "
                                      "Systém skladovania vodíka", "nazev_autoritativni": "",
                          "zdroj_autoritativni_url": "", "anotace_poznamka": "", "popis_autoritativni": ""},
                         "Rešerše Sinay uvádí část 2 (systém skladování vodíku); název a popis části 3 (IEC 63341-3) "
                         "přiřadilo dřívější stahování autoritativních údajů chybně. Název ze zdroje, popis odstraněn "
                         "(iec.ch automatické dotazy odmítá)."),
    "ASTM E1529-22": ({"nazev_cz": "Standard Test Methods for Determining Effects of Large Hydrocarbon Pool Fires on "
                                   "Structural Members and Assemblies"},
                      "Z názvu odstraněna přípona „, 2016e1“ staršího vydání; označení je vydání 2022."),
    "ES-TRIN": ({"nazev_cz": "Europäischer Standard der technischen Vorschriften für Binnenschiffe (ES-TRIN)"},
                "ES-TRIN je evropský standard technických požadavků na plavidla vnitrozemské plavby (CESNI); "
                "požadavky na alternativní paliva jsou jeho částí, popis ze zdroje to uvádí."),
    "TRGS 3146 / TRGS 726": ({"znacka": "TRBS 3146 / TRGS 726", "nazev_cz": "Ortsfeste Druckanlagen für Gase"},
                             "Název patřil sousednímu předpisu TRBS 3145 / TRGS 725 (ortsbewegliche "
                             "Druckgasbehälter); popis ze zdroje odpovídá TRBS 3146 / TRGS 726 (ortsfeste "
                             "Druckanlagen für Gase), označení předpisu je TRBS, ne TRGS 3146 (BAuA)."),
}
NO_SOURCE = {
    "124/2000 Z. z.": "popis doplněný modelem uváděl ochranu životního prostředí, vyhláška upravuje požární bezpečnost",
    "94/2004 Z. z.": "popis doplněný modelem odporuje názvu (protipožární bezpečnost staveb)",
    "96/2004 Z. z.": "popis doplněný modelem odporuje názvu (protipožární bezpečnost hořlavých kapalin)",
    "699/2004 Z. z.": "popis doplněný modelem odporuje názvu (zabezpečení staveb vodou na hašení)",
    "(EU) 2018/2001": "místo popisu odkaz na stránku Komise o infrastruktuře alternativních paliv",
    "(EU) 2018/2001 [EN]": "místo popisu odkaz na stránku Komise o infrastruktuře alternativních paliv",
    "(EU) 402/2013": "popis doplněný modelem zasadil železniční bezpečnostní metodu do vodíkových systémů",
    "(EU) 402/2013 [EN]": "popis doplněný modelem zasadil železniční bezpečnostní metodu do vodíkových systémů",
    "EN 17339": "popis doplněný modelem popisoval obecně vodíková zařízení, ne kompozitní lahve a trubky",
    "STN EN 1555-3/ - 2021.10": "popis patří obecné části EN 1555-1",
    "STN EN 1555-4/ - 2021.10": "popis patří obecné části EN 1555-1",
    "STN EN 60079-13/ - 2018.04": "popis patří části 11 (jiskrová bezpečnost), ne části 13",
    "API SPEC 11D1": "popis je úvod normy ASME B31.12 (posunutý řádek zdroje)",
    "API SPEC 5CT": "popis je úryvek normy ASME B31.12 (posunutý řádek zdroje)",
}
MERGES = {
    "/ - 2024.08": ("STN EN IEC 60079-26", "konec názvu STN EN IEC 60079-26 z dalšího řádku PDF rešerše Sinay"),
    "A1/ - 2024.03": ("STN EN ISO 11114-1/Zmena", "konec názvu změny A1 STN EN ISO 11114-1 z dalšího řádku PDF"),
    "NACE MR 0175 and 01-77": ("NACE MR 0175 and 01-77 Part 1", "neúplný název části I, úplný má dokument Part 1"),
    "Part 1": ("NACE MR 0175 and 01-77 Part 1", "konec názvu části I z dalšího řádku PDF rešerše Sinay"),
    "Part 2": ("NACE MR 0175 and 01-77 Part 2", "konec názvu části II z dalšího řádku PDF rešerše Sinay"),
    "ASTM F1624-12 @Sinay_Normy": ("ASTM F1624-12", "tatáž norma z rešerše Sinay (záznam bez označení)"),
    "SAE J2578 @Sinay_Normy": ("SAE J2578", "tatáž norma z rešerše Sinay (záznam bez označení)"),
    "AGBF- Leitfaden – Wasserstoff": ("AGBF- Leitfaden – Wasserstoff und dessen Gefahren", "tentýž leták AGBF"),
    "STN EN 14638-3/AC – 2010.12": ("STN EN 14638-3/ - 2010.12", "oprava AC je součástí normy, ne samostatný dokument"),
    "prEN IEC 62282-2-400": ("DIN EN IEC 62282-2-400", "návrh prEN byl vydán jako EN IEC 62282-2-400"),
    "IEC/TS 62933-5-1": ("IEC 62933-5-1", "technickou specifikaci nahradila mezinárodní norma IEC 62933-5-1"),
    "DIN ISO 19884": ("ISO/FDIS 19884-1", "DIN ISO 19884 neexistuje („dosiaľ neprijatý súbor“), jde o projekt ISO 19884-1"),
}
OUT_OF_SCOPE_SOURCE = "EU_Transposition_Targets_Import"


def entry(changes=None, reason="", **extra):
    out = {"changes": changes} if changes else {}
    out.update(extra)
    out.update({"confirmed_at": TODAY, "confirmed_by": BY, "reason": reason + f" ({DOC}; rozhodl uživatel {TODAY})"})
    return out


def load(cursor):
    cursor.execute("SELECT d.id, d.identifier, d.title, d.slug, dt.name, d.language, d.zdroj_dat, "
                   "COALESCE(NULLIF(d.popis_autoritativni, ''), NULLIF(d.description, '')) "
                   "FROM Document d LEFT JOIN DocumentType dt ON dt.id = d.type_id ORDER BY d.id")
    return [dict(zip(("id", "identifier", "title", "slug", "type", "language", "source", "description"), r))
            for r in cursor.fetchall()]


def target_designation(record):
    """The designation the database uses for an ISO record: published -> "ISO 19880-7",
    in progress -> its reference ("ISO/DIS 19885-2")."""
    return iso_open_data.base_reference(record["reference"])


def iso_plan(documents, index, findings):
    """[(key, entry)] of the ISO step and [(doc, record)] of what it changes."""
    drafts_published = {f["id"] for f in findings if f["check"] == "iso_draft_published"}
    duplicate_ids = {f["id"] for f in findings if f["check"] == "duplicate_title"} | \
                    {f.get("other_id") for f in findings if f["check"] == "duplicate_title"}
    groups = collections.defaultdict(list)
    for doc in documents:
        ident = doc["identifier"] or ""
        if doc["type"] != "Norma" or not ident.startswith("ISO"):
            continue
        international = ISO_OVERRIDE.get(doc["id"]) or fetch_ics.international_part(ident)
        record = iso_open_data.lookup(index, international) if international else None
        if record and not abandoned(record):
            groups[record["id"]].append((doc, record))
    survivors, merges, report = [], [], []
    for members in groups.values():
        record = members[0][1]
        stage = record.get("currentStage") or 0
        if stage >= iso_open_data.WITHDRAWN:
            continue
        target = target_designation(record)
        ids = {doc["id"] for doc, _ in members}
        core = lambda d: iso_open_data.base_reference(d["identifier"])  # noqa: E731
        needed = (len(members) > 1 or ids & (drafts_published | ISO_ERRORS | duplicate_ids)
                  or any(STAGE_PREFIX.match(core(d)) and core(d) != target for d, _ in members))
        if not needed:
            continue
        exact = [d for d, _ in members if d["identifier"] == target] or [d for d, _ in members if core(d) == target.upper()]
        survivor = exact[0] if exact else min((d for d, _ in members), key=lambda d: d["id"])
        scope = " ".join(re.sub(r"<[^>]+>", " ", (record.get("scope") or {}).get("en") or "").split())
        title = (record.get("title") or {}).get("en")
        url = f"https://www.iso.org/standard/{record['id']}.html"
        changes = {"nazev_cz": title, "nazev_autoritativni": title, "zdroj_autoritativni_url": url}
        if scope:
            changes.update({"anotace_poznamka": scope, "popis_autoritativni": scope})
        if survivor["identifier"] != target:  # also drops an edition date ("ISO 11326/ - 2024.011")
            changes.update({"znacka": target, "slug": survivor["slug"]})
        survivors.append((survivor["identifier"], entry(
            changes, f"Údaje podle otevřených dat ISO ({record['reference']}, stav {stage}): označení, název a "
                     f"anotace normy")))
        report.append((survivor, target, record, "update"))
        for doc, _ in members:
            if doc["id"] != survivor["id"]:
                merges.append((doc["identifier"], entry(None, f"Tentýž projekt ISO jako {target} "
                                                              f"({record['reference']}); sloučeno",
                                                        merged_into=target)))
                report.append((doc, target, record, "merge"))
    return survivors, merges, report


def build(documents, index, findings):
    by_identifier = {d["identifier"]: d for d in documents if d["identifier"]}
    survivors, iso_merges, report = iso_plan(documents, index, findings)
    planned = dict(survivors)
    for doc_id, designation in ISO_DESCRIPTION.items():
        doc = next(d for d in documents if d["id"] == doc_id)
        record = iso_open_data.lookup(index, designation)
        scope = " ".join(re.sub(r"<[^>]+>", " ", (record.get("scope") or {}).get("en") or "").split())
        planned[doc["identifier"]] = entry({"anotace_poznamka": scope, "popis_autoritativni": scope},
                                           f"Popis patřil jiné normě; nahrazen anotací {record['reference']} z "
                                           f"otevřených dat ISO")
    for key, (changes, reason) in MANUAL.items():
        planned[key] = entry(changes, reason)
    for key, reason in NO_SOURCE.items():
        planned[key] = entry({"anotace_poznamka": "", "popis_autoritativni": ""},
                             f"Popis odstraněn: {reason}; zdroj anotaci nenabízí, dokument čeká na doplnění popisu")
    for key, value in iso_merges:
        planned[key] = value
    for key, (target, reason) in MERGES.items():
        planned[key] = entry(None, f"Duplicita: {reason}; sloučeno do {target}", merged_into=target)
    out_of_scope = [d for d in documents if d["source"] == OUT_OF_SCOPE_SOURCE
                    and any(f["id"] == d["id"] and f["check"] == "model_relevance" for f in findings)]
    for doc in out_of_scope:
        planned[doc["identifier"]] = entry(None, "Mimo rozsah databáze (doc/DATABASE_SCOPE.md): akt EU doplněný jako "
                                                 "cíl transpozice citovaný v českém zákoně, bez vztahu k vodíkovým "
                                                 "technologiím; vyřazeno z katalogu", exclude=True)
    missing = [k for k in planned if k.split(" @")[0] not in by_identifier and not k.endswith(" [EN]")]
    return planned, report, out_of_scope, missing


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--write", action="store_true", help="add the corrections to data/manual_corrections.json")
    args = parser.parse_args(argv)
    conn = dterms.connect(args.env_file)
    try:
        documents = load(conn.cursor())
    finally:
        conn.close()
    findings = (json.loads(cr.REPORT_PATH.read_text(encoding="utf-8"))["findings"]
                + json.loads((state_paths.data_file("record_checks_model.json")).read_text(encoding="utf-8"))["findings"])
    planned, report, out_of_scope, missing = build(documents, iso_open_data.load_index(), findings)
    for doc, target, record, action in report:
        print(f"ISO {action:6s} #{doc['id']} {doc['identifier']!r} -> {target} ({record['reference']}, {record.get('currentStage')})")
    print(f"corrections: {len(planned)} (out of scope: {len(out_of_scope)})")
    for key in missing:
        print(f"[warn] no live document with identifier {key!r}")
    if args.write:
        corrections = json.loads(MANUAL_CORRECTIONS_PATH.read_text(encoding="utf-8"))
        for key, value in planned.items():
            old = corrections.get(key)
            if old is None or old.get("confirmed_at") == TODAY:
                corrections[key] = value  # a new one, or one this script wrote before
                continue
            clash = set(old.get("changes", {})) & set(value.get("changes", {}))
            if clash or "changes" not in value or old.get("merged_into") or old.get("exclude"):
                print(f"[warn] {key!r} already has a correction ({', '.join(sorted(clash)) or 'merge/exclude'}) — kept")
                continue
            old.setdefault("changes", {}).update(value["changes"])
            old["reason"] = old.get("reason", "") + " " + value["reason"]
            old["confirmed_at"] = TODAY
            print(f"{key!r}: changes added to its correction")
        MANUAL_CORRECTIONS_PATH.write_text(json.dumps(corrections, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"written to {MANUAL_CORRECTIONS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
