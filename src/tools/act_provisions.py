"""The opening provision of a legal act, taken word for word from its clean full text
(issue #37, doc/ANOTACE_PREDPISU.md).

A Czech or Slovak act usually opens with "§ 1 Předmět úpravy" ("Tento zákon upravuje …"),
an EU act with "Článek 1 Předmět" / "Article 1 Subject matter" ("Tato směrnice stanoví …").
That provision says what the act regulates in the act's own words — or, in an EU act, its purpose ("Účelem této
směrnice je …") or the annex it adopts ("Přijímá se technická specifikace …") — so it may
stand as the description of the document (principle 7 of doc/PROVOZ.md: a description comes from the
source or from the text of the document).

`opening_provision(text, language)` finds it in a clean text (data/fulltext_clean/,
one provision heading per line) and decides whether it may stand as the description: not
when the act only amends another one ("Zákon č. … se mění takto", "Přílohy … se nahrazují"),
when the provision only lists the transposed EU directives, or when it defines terms.
"""
import re
import unicodedata

MAX_LENGTH = 1500

# the heading line of the first provision, per language
_FIRST = {
    "CS": re.compile(r"^(§\s*1|Článek\s+1|Čl\.\s*1)\s*$", re.M),
    "SK": re.compile(r"^(§\s*1|Článok\s+1|Čl\.\s*1)\s*$", re.M),
    "EN": re.compile(r"^(Article\s+1|§\s*1)\s*$", re.M),
}
_SECOND = {
    "CS": re.compile(r"^(§\s*2|Článek\s+2|Čl\.\s*2|ČÁST\s+DRUHÁ|HLAVA\s+II)\s*$", re.M),
    "SK": re.compile(r"^(§\s*2|Článok\s+2|Čl\.\s*2|DRUHÁ\s+ČASŤ|HLAVA\s+II)\s*$", re.M),
    "EN": re.compile(r"^(Article\s+2|§\s*2|CHAPTER\s+II)\s*$", re.M),
}
# a heading that names the subject matter of the act
SUBJECT_HEADINGS = re.compile(
    r"^(Předmět(\s+úpravy)?(\s+a\s+(oblast\s+působnosti|účel))?|Oblast\s+působnosti|Účel(\s+a\s+předmět)?(\s+zákona)?|"
    r"Úvodní\s+ustanovení|Predmet(\s+úpravy)?(\s+a\s+rozsah\s+pôsobnosti)?|Rozsah\s+pôsobnosti|Účel|"
    r"Subject\s+matter(\s+and\s+scope)?|Scope(\s+and\s+subject\s+matter)?|Subject\s+matter,\s+scope.*)\s*$", re.I)
# verbs saying what the act regulates (a provision with a transposition clause needs one)
SUBJECT_VERBS = re.compile(
    r"\b(upravuje|upravují|stanoví|stanovuje|stanovují|vymezuje|se\s+vztahuje|se\s+vztahují|zřizuje|zavádí|"
    r"ustanovuje|ustanovujú|sa\s+vzťahuje|vymedzuje|zriaďuje|"
    r"lays\s+down|establishes|sets\s+out|applies\s+to|shall\s+apply\s+to|governs)\b", re.I)
AMENDING = re.compile(r"\bse\s+mění\s+takto\b|\bsa\s+mení\s+a\s+dopĺňa\s+takto\b|\bsa\s+mení\s+takto\b|"
                      r"\bis\s+amended\s+as\s+follows\b|\bare\s+amended\s+as\s+follows\b|"
                      r"\bse\s+nahrazuj[eí]\b|\bse\s+mění\s+v\s+souladu\s+s\s+přílohou\b|\bsa\s+nahrádza(jú)?\b|"
                      r"\bis\s+replaced\s+by\b|\bare\s+replaced\s+by\b", re.I)
TRANSPOSITION_ONLY = re.compile(r"\b(zapracovává|zapracúva|transponuje|preberá)\b", re.I)
DEFINITIONS = re.compile(r"^(Definice|Definície|Definitions|Pojmy|(Vymezení|Vymedzenie|Výklad)(\s+\w+)?\s+(pojmů|pojmov)|"
                         r"(Základní|Základné)\s+pojmy)\s*$", re.I)
_DEFINING = re.compile(r"^(\(\d+\)\s*)?(Pro\s+účely\s+(tohoto|této|tohoto)|Na\s+účely\s+(tohto|tejto)|"
                       r"For\s+the\s+purposes\s+of\s+this)\b", re.I)
# a heading saying what the provision is about, beyond the subject matter: "Účel zákona", "Cieľ …"
_PURPOSE_HEADINGS = re.compile(r"^(Účel|Cíl|Cíle|Cieľ|Ciele|Objective|Purpose|Aim)", re.I)
# a sentence, not a heading: "Tento zákon", "Táto vyhláška", "This Regulation"
_SENTENCE_START = re.compile(r"^(Tento|Tato|Toto|Táto|Tieto|This|These)\b")
# a footnote mark glued to a word ("Unie1)", "Unie1a)")
_FOOTNOTE = re.compile(r"(?<=[^\W\d_]|[,.;:])\d{1,3}[a-z]?\)")


def clean_provision(body):
    """The body of a provision as running text: footnote marks out, lines joined (a
    numbered paragraph "(2)" or point "a)" keeps its own line)."""
    body = _FOOTNOTE.sub("", body)
    lines = [" ".join(line.split()) for line in body.splitlines() if line.strip()]
    out = []
    for line in lines:
        if out and not re.match(r"^(\(\d+\w?\)|\d+\.|[a-z]\)|[ivx]+\))\s", line):
            out[-1] += " " + line
        else:
            out.append(line)
    return "\n".join(out).strip()


def shorten(text, limit=MAX_LENGTH):
    """`text` cut at the last paragraph or sentence end within `limit`, with "…"."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for mark in ("\n", ". ", "; "):
        position = cut.rfind(mark)
        if position > limit // 2:
            return cut[:position + 1].rstrip() + " …"
    return cut.rsplit(" ", 1)[0] + " …"


def opening_provision(text, language="CS"):
    """{"label", "heading", "text", "usable", "reason"} of the first provision of an act,
    or None when the text has none. `usable` tells whether it describes what the act
    regulates; `reason` says why not."""
    language = (language or "CS").upper()
    first = _FIRST.get(language, _FIRST["CS"]).search(text or "")
    if not first:
        return None
    rest = text[first.end():]
    end = _SECOND.get(language, _SECOND["CS"]).search(rest)
    block = rest[:end.start()] if end else rest[:6000]
    lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
    heading = ""
    if (lines and len(lines[0]) <= 90 and not lines[0].endswith((".", ":", ";")) and not re.match(r"^\(\d", lines[0])
            and not _SENTENCE_START.match(lines[0])):
        heading, lines = lines[0], lines[1:]
    body = clean_provision("\n".join(lines))
    label = " ".join(first.group(1).split())
    result = {"label": label, "heading": heading, "text": shorten(body), "full_length": len(body)}
    reason = None
    if not body:
        reason = "prázdné ustanovení"
    elif DEFINITIONS.match(heading) or _DEFINING.match(body):
        reason = "první ustanovení vymezuje pojmy"
    elif AMENDING.search(body[:400]):
        reason = "novela: ustanovení jen mění jiný předpis"
    elif TRANSPOSITION_ONLY.search(body) and not SUBJECT_VERBS.search(body) and len(body) < 600:
        reason = "ustanovení jen vyjmenovává transponované předpisy EU"
    elif (heading and not SUBJECT_HEADINGS.match(heading) and not _PURPOSE_HEADINGS.match(heading)
          and not SUBJECT_VERBS.search(body[:400]) and not re.search(r"\b(účelem|cílem|účelom|cieľom|aims?\s+to)\b", body[:400], re.I)):
        reason = f"první ustanovení („{heading}“) nepopisuje předmět předpisu"
    result.update(usable=reason is None, reason=reason)
    return result


def label_of(provision, language="CS"):
    """How the description names its source: "§ 1 Předmět úpravy", "čl. 1 Předmět"."""
    label = provision["label"]
    label = re.sub(r"^(Článek|Článok|Čl\.)\s*", "čl. ", label)
    label = re.sub(r"^Article\s*", "Art. ", label)
    return f"{label} {provision['heading']}".strip()


# a preamble or an enacting formula: "Ministerstvo dopravy stanoví podle § 137 …:", "… ustanovuje:"
_ENACTING = re.compile(r"^(Ministerstvo|Vláda|Národní\s+rada|Parlament|Ministerstvo\s+\w+)\b.*\b(stanoví|nařizuje|ustanovuje|"
                       r"se\s+usnesl|uznesla)\b.*:\s*$", re.I | re.S)
_DESCRIBING = re.compile(SUBJECT_VERBS.pattern + r"|\b(účelem|cílem|účelom|cieľom|aims?\s+to|purpose|objective|"
                         r"se\s+týká|se\s+použije|se\s+provádí|přijímá\s+se|přijímají\s+se|mění\b[^.]{0,80}?\btak,\s+aby)\b", re.I)


# the act speaks of itself: "Tato směrnice …", "této směrnice", "This Regulation"
_THIS_ACT = re.compile(r"\b(tato|této|touto|toto|tohoto|tímto|tento|tohto|táto|tejto|this)\s+"
                       r"(směrnic\w*|nařízení|rozhodnutí|zákon\w*|vyhlášk\w*|smernic\w*|nariaden\w*|directive|regulation|decision)\b", re.I)


def describes(text, label=""):
    """None when a quoted provision may stand as the description, else why not — the
    checks of opening_provision() applied to a provision a model located. A recital
    ("bod odůvodnění") must speak of the act itself, not of the act it amends."""
    body = " ".join((text or "").split())
    if re.search(r"odůvodnění|recital|preambul", label or "", re.I) and not _THIS_ACT.search(body):
        return "bod odůvodnění nemluví o tomto předpisu"
    if len(body) < 80:
        return "citace je příliš krátká"
    if body.rstrip().endswith(":"):
        return "citace končí dvojtečkou (výčet nebo úvodní věta)"
    if AMENDING.search(body[:400]):
        return "novela: citace jen mění jiný předpis"
    if _DEFINING.match(body):
        return "citace vymezuje pojmy"
    if _ENACTING.match(body):
        return "citace je úvodní věta předpisu, ne jeho obsah"
    if re.match(r"^(\(\d+\)\s*)?(Táto|Tato|Tento|Toto|This)\s+\w+\s+sa\s+nevzťahuje|^(\(\d+\)\s*)?\w+\s+\w+\s+se\s+nevztahuje", body):
        return "citace vymezuje jen výjimky z působnosti"
    if not _DESCRIBING.search(body):
        return "citace neříká, co předpis upravuje"
    return None


# --- the description an act gets (annotate_acts.py, build_unified_db.py, init_db.py) ----------

LEGAL_TYPES = ("Zákon", "Vyhláška", "Nařízení vlády", "Směrnice EU", "Nařízení EU", "Rozhodnutí EU")
SOURCE_NOTE = "doslova z textu předpisu"
MANUAL_REASON = "popis je třeba doplnit ručně"
# "Zákon č. 100/2001 Sb. - Zákon o …", "Nařízení vlády č. 192/2022 Sb. - …": the official full title
_CZ_TITLE_DESCRIPTION = re.compile(r"^(Zákon|Vyhláška|Nařízení\s+vlády)\b[^.\n]{0,60}?č\.\s*\d+/\d{4}\s*Sb\.\s*[-–—]", re.I)


def _fold(text):
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def restates_title(description, *titles):
    """True when `description` only restates the title of the act: the official full
    title of a Czech act ("Zákon č. 100/2001 Sb. - Zákon o …"), or a text whose words
    are nearly all in the title and that is hardly longer."""
    description = (description or "").strip()
    if not description:
        return False
    if _CZ_TITLE_DESCRIPTION.match(description) and len(description) < 400:
        return True
    words = set(re.findall(r"[a-z]{3,}", _fold(description)))
    title_words = set(re.findall(r"[a-z]{3,}", _fold(" ".join(t or "" for t in titles))))
    longest = max((len(t or "") for t in titles), default=0)
    return bool(words) and len(words & title_words) / len(words) >= 0.8 and len(description) <= 1.5 * longest + 40


def description_of(entry):
    """(description, popis_zdroj, popis_priblizny) a cache entry of data/act_descriptions.json
    gives an act: its opening provision (found by the pattern, or located by a model and
    checked), else the checked approximate summary, else nothing."""
    located = entry.get("located") or {}
    provision = entry.get("provision") or (located if located.get("found") else None)
    if provision:
        label = provision.get("label") or ""
        if re.fullmatch(r"\d+(\.\d+)*", label):  # a point of a UN/ECE regulation: "1" -> "bod 1"
            label = f"bod {label}"
        method = "" if provision.get("method") == "pattern" else ", ustanovení vyhledal jazykový model"
        return provision["text"], f"{label}, {SOURCE_NOTE}{method}".strip(", "), None
    return None, None, (entry.get("summary") or {}).get("summary")
