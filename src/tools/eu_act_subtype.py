"""Subtype of an EU legal act: delegated act (akt v přenesené pravomoci, Art. 290
TFEU) or implementing act (prováděcí akt, Art. 291 TFEU) — doc/MPO_PRIPOMINKY.md,
připomínka 3 and krok 2. The value lands in `Document.eu_act_subtype`
('delegated' / 'implementing' / NULL), set by init_db.py on every rebuild and by
backfill_eu_act_subtype.py for an existing database; the catalogue only reads it.

Decided from evidence, never guessed, in this order:
  1. the ELI of the record's URL (`eli/reg_del/…`, `eli/dir_impl/…`): the
     Publications Office's own classification;
  2. the official title, in Czech, Slovak or English: "v přenesené pravomoci",
     "delegované nařízení", "Commission Delegated Regulation"; "prováděcí
     nařízení/rozhodnutí/směrnice", "vykonávacie nariadenie", "Implementing
     Regulation/Decision/Directive" (in English only after "Commission"/"Council").
A CELEX number does not tell the two apart (both are 3yyyyRnnnn), so it is not used.

Only EU acts qualify: the document must be in the EU jurisdiction or have an
EUR-Lex URL; a methodology that merely mentions "the Delegated Act" in its title
is not one. "Prováděcí" has to name the act itself ("Prováděcí nařízení Komise"),
not a phrase like "o prováděcích pravidlech" in a pre-Lisbon title.
"""
import re

DELEGATED = "delegated"
IMPLEMENTING = "implementing"
SUBTYPES = (DELEGATED, IMPLEMENTING)

_ELI = re.compile(r"/eli/(?:reg|dir|dec)_(del|impl)/", re.IGNORECASE)

_ACT = r"(?:nařízení|rozhodnutí|směrnice|nariadenie|rozhodnutie|smernica|regulation|decision|directive)"
_DELEGATED_TITLE = re.compile(
    r"v\s+přenesené\s+pravomoci"
    r"|delegovan[éá]\s+" + _ACT +
    r"|delegated\s+" + _ACT,
    re.IGNORECASE)
_IMPLEMENTING_TITLE = re.compile(
    r"(?:prováděcí|vykonávacie|vykonávacia)\s+" + _ACT +
    r"|(?:commission|council)\s+implementing\s+" + _ACT,
    re.IGNORECASE)


def is_eu_act(jurisdikce, url):
    return (jurisdikce or "").strip() == "EU" or "eur-lex.europa.eu" in (url or "").lower()


def classify(title, url, jurisdikce):
    """'delegated', 'implementing' or None."""
    if not is_eu_act(jurisdikce, url):
        return None
    eli = _ELI.search(url or "")
    if eli:
        return DELEGATED if eli.group(1).lower() == "del" else IMPLEMENTING
    text = re.sub(r"\s+", " ", (title or "").replace("\xa0", " "))
    # The act's own designation comes first in its title; a later mention is
    # another act it amends or supplements ("…, kterým se mění … rozhodnutí
    # Komise v přenesené pravomoci (EU) 2017/1474" in an implementing act).
    found = [(m.start(), subtype) for subtype, pattern in ((DELEGATED, _DELEGATED_TITLE),
                                                           (IMPLEMENTING, _IMPLEMENTING_TITLE))
             for m in [pattern.search(text)] if m]
    return min(found)[1] if found else None
