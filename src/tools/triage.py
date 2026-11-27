"""Automatic triage of the candidate queue (`DocumentCandidate`, candidates.py),
doc/FRONTA_AUTOMAT.md.

Two steps, both run by the technical account `automat` (candidates.AUTOMAT_USERNAME),
which never signs in and never confirms anything:

1. **Rules** (data/triage_rules.json, data, not code, so the user approves the list
   before it first runs over the live database): the first rule whose condition
   matches decides — propose the acceptance (a human editor then confirms it), reject
   or defer (both reversible: an editor reopens the candidate), or hand the candidate
   to the model.
2. **The language model** (OpenAI, `model.name` in the rules file, default
   gpt-4o-mini) assesses the rest: it gets only public data (designation, title,
   address, the public excerpts of the evidence, the titles of the citing documents,
   the scope of the database) and returns a structured recommendation. Above the
   thresholds of the configuration the automat proposes the acceptance, or rejects or
   defers in the categories the user approved (`model.auto_categories`); otherwise the
   recommendation is only stored for the editors. Answers are cached in
   data/triage_model_cache.json, so nothing is sent twice.

Every action goes through the same validation as an editor's proposal
(candidates.validate_proposal) and is written to the AuditLog under the automat's
account, with the rule and the reason.
"""
import collections
import datetime
import hashlib
import json
import pathlib
import re
import time

import candidates as cd
import citation_closure as cc
import vocabulary
import state_paths

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
RULES_PATH = REPO_ROOT / "data" / "triage_rules.json"
CACHE_PATH = state_paths.data_file("triage_model_cache.json")
SCOPE_PATH = REPO_ROOT / "doc" / "DATABASE_SCOPE.md"
API_KEY_PATH = REPO_ROOT / ".openapi_key"

ACTIONS = ("propose", "reject", "defer", "model")
RECOMMENDATIONS = ("accept", "reject", "defer")
CATEGORIES = {
    "v_rozsahu": "patří do rozsahu databáze",
    "mimo_rozsah": "věcně mimo okruhy databáze",
    "dane_dotace": "daně, poplatky, ceny, rozpočet (mimo rozsah podle DATABASE_SCOPE.md, odst. 3)",
    "fondy_zakazky": "daně a dotace: fondy, podpůrné programy, veřejné zakázky",
    "obecne_vyrobky": "obecný předpis o výrobcích (posuzování shody, dozor nad trhem, EMC, strojní a tlaková zařízení)",
    "neni_dokument": "není regulační dokument (zpráva, novinka, prezentace, webinář)",
    "zastaraly": "historický nebo neúčinný předpis bez významu pro dnešní praxi",
    "zahranicni": "předpis jiného státu, mimo ČR, EU a mezinárodní úroveň",
    "nejiste": "nelze rozhodnout z dostupných údajů",
}
RECOMMENDATION_LABELS = {"accept": "přijmout", "reject": "zamítnout", "defer": "odložit"}
ACTION_LABELS = {"propose": "navržen k přijetí", "reject": "zamítnut", "defer": "odložen",
                 "model": "k posouzení modelem", "recommend": "jen doporučení"}
_CZECH_LETTERS = re.compile(r"[áčďéěíňóřšťúůýž]", re.I)


# --- configuration -----------------------------------------------------------

def load_config(path=None):
    config = json.loads(pathlib.Path(path or RULES_PATH).read_text(encoding="utf-8"))
    for rule in config["rules"]:
        if rule["action"] not in ACTIONS:
            raise ValueError(f"rule {rule['id']}: unknown action {rule['action']!r}")
    return config


def is_approved(config):
    approval = config.get("approval") or {}
    return bool(approval.get("approved_by") and approval.get("date"))


# --- the documents already in the database -------------------------------------

def _norm_designation(text):
    text = re.sub(r"\s+", " ", (text or "").upper()).strip()
    text = re.sub(r"\s+ED\.\s*\d+$", "", text)
    return re.sub(r":\s*\d{4}$", "", text)


def document_index(documents, areas=None, validity=None):
    """{"keys": {CZ/EU key: [(id, identifier, language)]}, "designations": {normalised identifier: id},
    "areas": {id: [subject area]}, "validity": data/validity_cache.json} of the documents of the database,
    `documents` = [(id, identifier, title, language)]."""
    keys, designations = collections.defaultdict(list), {}
    for doc_id, identifier, title, language in documents:
        for key in cc.own_keys(identifier, title):
            if key.split(":", 1)[0] in ("CZ", "EU"):
                keys[key].append((doc_id, identifier, language))
        if identifier:
            designations.setdefault(_norm_designation(identifier), doc_id)
    return {"keys": dict(keys), "designations": designations, "areas": areas or {}, "validity": validity or {}}


def candidate_language(candidate):
    return candidate.get("language") or guess_language(candidate.get("title"))


def same_act(candidate, index):
    """[(id, identifier, language)] of the documents of the database that are the act of
    the candidate in any language (the same Czech or EU key)."""
    key = candidate.get("candidate_key") or ""
    keys = {key} if key.split(":", 1)[0] in ("CZ", "EU") else set()
    if candidate.get("designation"):
        keys |= cd.act_keys(candidate["designation"])
    found = {}
    for k in sorted(keys):
        for document in index["keys"].get(k, []):
            found.setdefault(document[0], document)
    return [found[i] for i in sorted(found)]


def duplicate_of(candidate, index):
    """(document id, explanation) of the document of the database the candidate already
    is IN ITS LANGUAGE (rule R1), or None. Czech and EU acts are compared by their keys
    and languages, the rest (standards, technical rules) by the designation itself."""
    language = candidate_language(candidate)
    for doc_id, identifier, doc_language in same_act(candidate, index):
        if (doc_language or "CS") == language:
            return doc_id, f"v databázi je dokument #{doc_id} {identifier} ve stejném jazyce ({language})"
    key = candidate.get("candidate_key") or ""
    if candidate.get("designation") and not key.startswith("DRAFT") and not same_act(candidate, index):
        doc_id = index["designations"].get(_norm_designation(candidate["designation"]))
        if doc_id:
            return doc_id, f"v databázi je dokument #{doc_id} se stejným označením"
    return None


def language_variant_of(candidate, index):
    """The documents of the database that are the candidate's act in OTHER languages
    (rule R7), when none is in its language and the language has a designation
    convention (CS, EN, SK); else []."""
    others = same_act(candidate, index)
    if not others or duplicate_of(candidate, index) \
            or cd.variant_designation("x", candidate_language(candidate)) is None:
        return []
    return others


def repealing_acts(candidate, index):
    """The keys of the acts that repealed the candidate (its evidence or the validity cache)."""
    return cd.successors(candidate, candidate.get("evidence") or {}, index.get("validity") or {})


# --- rules -----------------------------------------------------------------------

def _matches(when, candidate, index):
    for field, expected in when.items():
        if field == "any":
            if not any(_matches(part, candidate, index) for part in expected):
                return False
        elif field == "duplicate":
            if bool(duplicate_of(candidate, index)) != expected:
                return False
        elif field == "language_variant":
            if bool(language_variant_of(candidate, index)) != expected:
                return False
        elif field == "has_document_type":
            present = bool(candidate.get("document_type")) and candidate["document_type"] != "Nezařazeno"
            if present != expected:
                return False
        elif field.endswith("_regex"):
            value = candidate.get(field[:-len("_regex")]) or ""
            if not re.search(expected, value):
                return False
        elif field == "tier":
            if (candidate.get("tier") or 1) not in expected:
                return False
        else:
            if candidate.get(field) not in expected:
                return False
    return True


def match_rule(candidate, config, index):
    """The first rule of the configuration whose condition the candidate meets."""
    for rule in config["rules"]:
        if _matches(rule.get("when") or {}, candidate, index):
            return rule
    raise ValueError("no rule matched; the last rule of the configuration must match everything")


def keyword_areas(text, config):
    text = (text or "").lower()
    return sorted(int(area) for area, words in config.get("area_keywords", {}).items()
                  if any(word.lower() in text for word in words))


def proposal_areas(candidate, rule, config, model=None):
    """The subject areas of a proposal: those the candidate already has (MPO tables), the
    model's, the rule's by designation, the keywords of the title, the rule's default."""
    own = cd.scope_areas(candidate)
    if own:
        return own
    if model and model.get("scope_areas"):
        return sorted({int(n) for n in model["scope_areas"] if int(n) in cd.SCOPE_AREAS})
    proposal = (rule or {}).get("proposal") or {}
    designation = candidate.get("designation") or ""
    prefixes = [p for p in proposal.get("areas_by_designation", {}) if designation.startswith(p)]
    if prefixes:
        return proposal["areas_by_designation"][max(prefixes, key=len)]
    found = keyword_areas(f"{designation} {candidate.get('title') or ''}", config)
    return found or list(proposal.get("default_areas") or [])


def guess_language(title):
    return "CS" if _CZECH_LETTERS.search(title or "") else "EN"


def guess_jurisdiction(candidate):
    key = candidate.get("candidate_key") or ""
    designation = candidate.get("designation") or ""
    if key.startswith(("CZ:", "DRAFT-CZ:", "DRAFT-NORM:CZ:")) or designation.startswith(("ČSN", "TPG")):
        return "CZ"
    if key.startswith(("EU:", "DRAFT-EU:")):
        return "EU"
    if key.startswith(("NORM:", "DRAFT-NORM:")):
        return "mezinárodní"
    return None


def proposal_metadata(candidate, rule, config, model=None, index=None):
    """(metadata, areas) of a proposal of acceptance by `rule` (or by the model's
    recommendation `model`), before validation."""
    defaults = (rule or {}).get("proposal") or {}
    model = model or {}
    title = candidate.get("title") or ""
    designation = candidate.get("designation") or ""
    if defaults.get("title_without_designation") and designation and title.startswith(designation):
        title = title[len(designation):].strip(" —-:")
    official = (model.get("official_title") or "").strip()
    if official and (not title or title.endswith("...") or title == designation):
        title = official
    document_type = defaults.get("document_type") or candidate.get("document_type")
    if (not document_type or document_type == "Nezařazeno") and model.get("document_type"):
        document_type = model["document_type"]
    own_areas = None
    if defaults.get("language_variant") and index is not None:
        others = language_variant_of(candidate, index)
        if others:  # the designation follows the convention of language_variants.py, the areas the other texts'
            designation = cd.variant_designation(others[0][1], candidate_language(candidate)) or designation
            own_areas = sorted({a for i, _, _ in others for a in index.get("areas", {}).get(i, [])})
    metadata = {
        "designation": designation,
        "title": title,
        "document_type": document_type or "",
        "url": candidate.get("url") or "",
        "language": defaults.get("language") or candidate.get("language") or guess_language(title),
        "jurisdikce": defaults.get("jurisdikce") or candidate.get("jurisdikce") or guess_jurisdiction(candidate) or "",
        "puvodce": cd.canonical_source(defaults.get("puvodce") or candidate.get("puvodce") or model.get("puvodce")),
    }
    return metadata, own_areas or proposal_areas(candidate, rule, config, model)


# --- the model ---------------------------------------------------------------------

def scope_text(path=None):
    """Sections 2.1, 3 and 4 of doc/DATABASE_SCOPE.md: what the database covers."""
    text = pathlib.Path(path or SCOPE_PATH).read_text(encoding="utf-8")
    parts = []
    for start, end in (("### 2.1", "### 2.2"), ("## 3.", "## 5.")):
        i, j = text.find(start), text.find(end)
        if i >= 0 and j > i:
            parts.append(text[i:j].strip())
    return "\n\n".join(parts)


def system_prompt(document_types, scope=None, composition=None):
    areas = "\n".join(f"{n}. {name}" for n, name in cd.SCOPE_AREAS.items())
    categories = "\n".join(f"- {k}: {v}" for k, v in CATEGORIES.items())
    held = f"\n\nCo databáze už obsahuje (počty dokumentů):\n{composition}" if composition else ""
    return f"""Jsi odborný asistent, který třídí kandidáty na zařazení do databáze regulačních předpisů \
k vodíkovým technologiím (projekt NAHYC, Česká republika). Kandidáta našla automatická kontrola: citace \
v textech databáze, sledovaný zdroj (Sbírka zákonů, Sněmovna, EUR-Lex, katalogy norem a technických \
pravidel, weby úřadů) nebo kontrola platnosti. Rozhodni, zda dokument do databáze patří.

Rozsah databáze (výňatek z dokumentu DATABASE_SCOPE.md):

{scope or scope_text()}{held}

Věcné okruhy (čísla použij v poli scope_areas):
{areas}

Typy dokumentů v databázi (pole document_type, jen z tohoto seznamu): {", ".join(document_types)}

Kategorie (pole category):
{categories}

Pokyny:
- Nejdřív napiš zdůvodnění (reasoning), potom rozhodni.
- recommendation: "accept" = dokument do databáze patří; "reject" = nepatří; "defer" = nelze rozhodnout \
nebo jde o zprávu či nález, který sám dokumentem není.
- Do rozsahu patří i obecné předpisy bez zmínky o vodíku, pokud upravují oblast některého okruhu \
(tlaková a plynová zařízení, výbušná prostředí, stavby, přeprava nebezpečných věcí, schvalování a provoz \
vozidel, metrologie, energetika, životní prostředí). Nepatří sem předpisy, v nichž se vodík nebo plyn \
objeví jen okrajově: zdravotnictví, potraviny, sociální zabezpečení, pracovní právo mimo BOZP, banky \
a finanční trh, obrana, statistika, myslivost a lesy, organizace státní správy.
- Daně, poplatky, mýtné, ceny a rozpočet: kategorie dane_dotace. Fondy (např. Nástroj pro oživení a odolnost, \
Fond pro spravedlivou transformaci, Státní fond dopravní infrastruktury), dotační a podpůrné programy, \
veřejná podpora, definice podniků pro účely podpor a zadávání veřejných zakázek: kategorie fondy_zakazky.
- Obecné předpisy o výrobcích a jejich uvádění na trh (posuzování shody a moduly, dozor nad trhem, \
akreditace, normalizace, elektromagnetická kompatibilita, strojní zařízení, tlaková zařízení, výrobky \
pro výbušné prostředí, nízké napětí), jde-li o dokument regulační povahy: kategorie obecne_vyrobky \
(recommendation „defer“).
- vztah_k_vodiku: true, týká-li se dokument vodíku, jeho výroby, skladování, přepravy či využití, \
RFNBO nebo palivových článků (výslovně, nebo je-li zjevné, že se na vodíková zařízení přímo vztahuje); \
jinak false. Zdůvodni jednou větou v poli vztah_k_vodiku_zduvodneni.
- Normy a technická pravidla: databáze vede i mezinárodní a zahraniční normy (ISO, IEC, EN, ČSN, DIN, SAE, \
ASME, CSA, EIGA, DVGW), pokud se týkají vodíku nebo okruhů databáze. Kategorie zahranicni platí jen \
pro právní předpisy jiných států, ne pro normy.
- Předpisy z doby před rokem 1990 o obchodních a celních dohodách, prozatímní platnosti úmluv a podobně \
jsou historické: reject, kategorie zastaraly. „Úplné znění“ zákona vyhlášené ve Sbírce není samostatný \
předpis: reject, kategorie zastaraly.
- Návrh předpisu (signál „návrh předpisu“) posuzuj podle toho, co mění: patří sem, mění-li předpis \
z okruhů databáze způsobem, který se okruhů týká.
- Novela (signál „novela dokumentu v databázi“) patří sem, mění-li dokument databáze věcně.
- scope_areas: všechny okruhy, kterých se dokument věcně týká (u přijetí aspoň jeden), jinak prázdné pole.
- confidence je pravděpodobnost 0–1, že je tvoje doporučení správné. Buď kalibrovaný: 0,95 jen u zcela \
jasných případů, u hraničních 0,5–0,7.
- official_title: úřední název dokumentu, jen pokud ho s jistotou znáš, jinak null. puvodce: \
vydávající instituce česky (např. „Ministerstvo průmyslu a obchodu“), jinak null.
- reasoning: zdůvodnění česky, nejvýše tři věty, věcně (proč patří či nepatří, do kterého okruhu).
Odpověz jen JSON podle schématu."""


def database_composition(cur, top=20):
    """Counts of the documents of the database by type and by issuer, for the prompt."""
    cur.execute("""SELECT t.name, COUNT(*) AS n FROM Document d JOIN DocumentType t ON t.id = d.type_id
                   GROUP BY t.name ORDER BY n DESC""")
    types = ", ".join(f"{r['name']} {r['n']}" for r in cur.fetchall())
    cur.execute("""SELECT s.name, COUNT(*) AS n FROM Document d JOIN DocumentSource s ON s.id = d.source_id
                   GROUP BY s.name ORDER BY n DESC, s.name LIMIT %s""", (top,))
    issuers = ", ".join(f"{r['name']} {r['n']}" for r in cur.fetchall())
    return f"podle typu: {types}\npodle původce (nejčastější): {issuers}"


def response_schema(document_types):
    return {
        "name": "candidate_assessment",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            # the reasoning first: the model thinks before it decides
            "required": ["reasoning", "recommendation", "category", "scope_areas", "document_type", "puvodce",
                         "official_title", "confidence", "vztah_k_vodiku", "vztah_k_vodiku_zduvodneni"],
            "properties": {
                "reasoning": {"type": "string"},
                "recommendation": {"type": "string", "enum": list(RECOMMENDATIONS)},
                "category": {"type": "string", "enum": list(CATEGORIES)},
                "scope_areas": {"type": "array", "items": {"type": "integer", "enum": list(cd.SCOPE_AREAS)}},
                "document_type": {"type": ["string", "null"], "enum": list(document_types) + [None]},
                "puvodce": {"type": ["string", "null"]},
                "official_title": {"type": ["string", "null"]},
                "confidence": {"type": "number"},
                "vztah_k_vodiku": {"type": "boolean"},
                "vztah_k_vodiku_zduvodneni": {"type": "string"},
            },
        },
    }


def _clip(text, limit):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def build_payload(candidate, linked, sources=None):
    """What the model gets about a candidate: public data only — the candidate's own
    metadata, the public excerpts of its evidence and the identifiers and titles of the
    documents of the database it is linked to (`linked` = {id: (identifier, title)}).
    Never the editors' names or notes (decision_note, proposed_by, ...)."""
    sources = sources or {}
    evidence = candidate.get("evidence") or {}
    payload = {"kandidat": {
        "oznaceni": candidate.get("designation"),
        "nazev": candidate.get("title"),
        "typ_podle_zdroje": candidate.get("document_type"),
        "adresa": candidate.get("url"),
        "jurisdikce": candidate.get("jurisdikce"),
        "zdroj": sources.get(candidate.get("source"), candidate.get("source")),
        "signal": cd.SIGNAL_LABELS.get(candidate.get("signal"), candidate.get("signal")),
        "platnost": candidate.get("validity_status"),
        "citovano_dokumenty_databaze": candidate.get("cited_by") or 0,
    }}
    findings = [{"zdroj": sources.get(f.get("source"), f.get("source")), "nazev": _clip(f.get("title"), 300),
                 "adresa": f.get("url"), "datum": f.get("date"), "uryvek": _clip(f.get("excerpt"), 500),
                 "poznamka_kontroly": f.get("note")}
                for f in (evidence.get("findings") or {}).values()]
    if findings:
        payload["nalezy"] = findings
    if evidence.get("mpo_rows"):
        payload["radky_tabulky_mpo"] = [{"cislo": r.get("cislo"), "nazev": r.get("nazev")} for r in evidence["mpo_rows"]]
    contexts = evidence.get("contexts") or {}
    citing = []
    for doc_id in (evidence.get("citing_ids") or [])[:5]:
        identifier, title = linked.get(doc_id, (None, None))
        places = (contexts.get(str(doc_id)) or {}).get("places") or []
        citing.append({"oznaceni": identifier, "nazev": _clip(title, 200),
                       "uryvky": [_clip(f"{p.get('before', '')}[{p.get('cited', '')}]{p.get('after', '')}", 400)
                                  for p in places[:2]]})
    if citing:
        payload["citujici_dokumenty"] = citing
        if len(evidence.get("citing_ids") or []) > 5:
            payload["citujicich_celkem"] = len(evidence["citing_ids"])
    elif evidence.get("context"):
        payload["kontext_citace"] = _clip(evidence["context"], 600)
    for field, label in (("amends_ids", "meni_dokumenty_databaze"), ("repeals_ids", "zrusil_dokumenty_databaze")):
        if evidence.get(field):
            payload[label] = [" ".join(x for x in linked.get(i, (None, None)) if x) for i in evidence[field][:10]]
    return payload


def estimate_tokens(text):
    """A rough count for the cost estimate: Czech text and JSON run about 2.8 characters a
    token (measured on the sample of 20 Nov 2026: 5.5 thousand tokens a candidate)."""
    return len(text) * 10 // 28 + 1


def cost(usage, prices):
    cached = usage.get("cached_tokens", 0)
    return ((usage.get("prompt_tokens", 0) - cached) * prices["input"] + cached * prices.get("cached_input", prices["input"])
            + usage.get("completion_tokens", 0) * prices["output"]) / 1_000_000


class ModelAssessor:
    """Calls the model for one candidate at a time, with every answer cached by the hash
    of the model, the prompt and the payload. `client` is an openai.OpenAI (or a fake in
    the tests); None loads the key from .openapi_key on the first call that needs it."""

    def __init__(self, config, document_types, cache_path=None, client=None, model=None, log=print, composition=None):
        self.settings = config["model"]
        self.model = model or self.settings["name"]
        self.document_types = list(document_types)
        self.system = system_prompt(self.document_types, composition=composition)
        # the cache key leaves the counts of the database out, so that accepting a document does not
        # invalidate every answer; a change of the instructions bumps model.prompt_version instead
        self.system_key = system_prompt(self.document_types)
        self.cache_path = pathlib.Path(cache_path or CACHE_PATH)
        self.cache = json.loads(self.cache_path.read_text(encoding="utf-8")) if self.cache_path.exists() else {}
        self.client = client
        self.log = log
        self.calls = 0
        self.usage = collections.Counter()

    def prices(self):
        return self.settings.get("prices_usd_per_million_tokens", {}).get(self.model)

    def key(self, payload):
        blob = json.dumps([self.model, self.settings.get("prompt_version"), self.system_key, payload],
                          ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def cached(self, payload):
        entry = self.cache.get(self.key(payload))
        return entry["result"] if entry else None

    def estimate(self, payloads):
        """(calls, input tokens, output tokens, USD or None) of assessing the payloads not cached yet."""
        todo = [p for p in payloads if self.cached(p) is None]
        system_tokens = estimate_tokens(self.system)
        tokens_in = sum(system_tokens + estimate_tokens(json.dumps(p, ensure_ascii=False)) for p in todo)
        tokens_out = 220 * len(todo)
        prices = self.prices()
        usd = cost({"prompt_tokens": tokens_in, "completion_tokens": tokens_out}, prices) if prices else None
        return len(todo), tokens_in, tokens_out, usd

    def _client(self):
        if self.client is None:
            import os
            from openai import OpenAI
            os.environ["OPENAI_API_KEY"] = API_KEY_PATH.read_text(encoding="utf-8").strip()
            self.client = OpenAI()
        return self.client

    def assess(self, payload, attempts=3):
        """The model's assessment (dict) of a candidate payload, or None after failed attempts."""
        cached = self.cached(payload)
        if cached is not None:
            return cached
        arguments = {"model": self.model, "messages": [
            {"role": "system", "content": self.system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            "response_format": {"type": "json_schema", "json_schema": response_schema(self.document_types)}}
        if self.model.startswith(("gpt-4", "gpt-3")):
            arguments["temperature"] = 0  # the reasoning models take only their default
            arguments["logprobs"] = True  # the probability of the recommendation (token_confidence)
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                completion = self._client().chat.completions.create(**arguments)
                result = json.loads(completion.choices[0].message.content)
                problem = check_assessment(result, self.document_types)
                if problem:
                    raise ValueError(problem)
                token = token_confidence(completion)
                if token is not None:
                    result["token_confidence"] = round(token, 4)
                usage = _usage(completion)
                self.calls += 1
                self.usage.update(usage)
                self.cache[self.key(payload)] = {"model": self.model, "at": _now(), "usage": usage, "result": result}
                self._save()
                return result
            except Exception as error:  # noqa: BLE001 — any failure leaves the candidate to the editors
                last_error = error
                if attempt < attempts:
                    time.sleep(2 * attempt)
        self.log(f"[warn] model failed after {attempts} attempts: {last_error}")
        return None

    def _save(self):
        tmp = self.cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self.cache_path)


def _usage(completion):
    usage = getattr(completion, "usage", None)
    if usage is None:
        return {}
    details = getattr(usage, "prompt_tokens_details", None)
    return {"prompt_tokens": usage.prompt_tokens or 0, "completion_tokens": usage.completion_tokens or 0,
            "cached_tokens": (getattr(details, "cached_tokens", 0) or 0) if details else 0}


def token_confidence(completion):
    """The probability the model gave to the first token of its recommendation (from the
    log probabilities), or None when they are not available. A self-reported confidence
    of a small model is a constant more often than not; this one is measured."""
    import math
    try:
        tokens = completion.choices[0].logprobs.content
    except AttributeError:
        return None
    if not tokens:
        return None
    text, starts = "", []
    for token in tokens:
        starts.append(len(text))
        text += token.token
    match = re.search(r'"recommendation"\s*:\s*"', text)
    if not match:
        return None
    position = match.end()
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        if start <= position < end:
            return math.exp(tokens[i].logprob)
    return None


def confidence(result):
    """The confidence the thresholds compare: the lower of the self-reported one and the
    measured probability of the recommendation."""
    values = [result["confidence"]] + ([result["token_confidence"]] if result.get("token_confidence") is not None else [])
    return min(values)


def check_assessment(result, document_types):
    """A message when the model's answer is not usable, else None."""
    if result.get("recommendation") not in RECOMMENDATIONS:
        return f"recommendation {result.get('recommendation')!r}"
    if result.get("category") not in CATEGORIES:
        return f"category {result.get('category')!r}"
    confidence = result.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        return f"confidence {confidence!r}"
    if result.get("document_type") not in list(document_types) + [None]:
        return f"document_type {result.get('document_type')!r}"
    if any(n not in cd.SCOPE_AREAS for n in result.get("scope_areas") or []):
        return f"scope_areas {result.get('scope_areas')!r}"
    return None


HYDROGEN = re.compile(r"vodík|vodíkov|hydrogen|wasserstoff|rfnbo|nebiologického původu|non-biological origin"
                      r"|palivov\w* článk|fuel[ -]cell|\bH2\b", re.I)


def hydrogen_in_text(candidate):
    """True when the candidate's own title or designation, the excerpts its sources
    found, or the places the database cites it name hydrogen (deterministic support of
    the model's `vztah_k_vodiku`)."""
    evidence = candidate.get("evidence") or {}
    texts = [candidate.get("title") or "", candidate.get("designation") or ""]
    texts += [f"{f.get('title') or ''} {f.get('excerpt') or ''}" for f in (evidence.get("findings") or {}).values()]
    for places in (evidence.get("contexts") or {}).values():
        texts += [f"{p.get('before', '')}{p.get('cited', '')}{p.get('after', '')}" for p in places.get("places") or []]
    if not evidence.get("contexts") and evidence.get("context"):
        texts.append(evidence["context"])
    return any(HYDROGEN.search(t) for t in texts)


def hydrogen_relation(result, candidate=None):
    """The candidate's relation to hydrogen: the model's answer, or hydrogen named in
    the candidate's texts (either suffices; a deferral is the cautious outcome)."""
    return bool(result.get("vztah_k_vodiku")) or (candidate is not None and hydrogen_in_text(candidate))


def effective_category(result, candidate, config):
    """(category, True) when the candidate's title matches a pattern of
    `model.category_patterns` (funds, programmes and procurement; general product
    rules), which the model, as the sample showed, often misses; else (the model's
    category, False). Standards are left to the model (a pattern names acts)."""
    if candidate is not None and candidate.get("document_type") != "Norma":
        for category, pattern in (config["model"].get("category_patterns") or {}).items():
            if re.search(pattern, candidate.get("title") or "", re.I):
                return category, True
    return result["category"], False


def model_action(result, config, candidate=None):
    """What the automat does with the model's answer: "propose", "reject", "defer", or
    "recommend" (the recommendation is only shown to the editors). Below the threshold
    nothing happens. A category the user approved (`model.auto_categories`: {category:
    {"action", "hydrogen"}}) decides first: a rejection only when the model recommends
    rejecting, an action with `"hydrogen": true` only for a candidate related to hydrogen.
    Otherwise an acceptance of a candidate within the scope becomes a proposal."""
    settings = config["model"]
    level = confidence(result)
    category, from_pattern = effective_category(result, candidate, config)
    if from_pattern:  # the title itself says what the document is: no doubt of the model applies
        level = 1.0
    rule = (settings.get("auto_categories") or {}).get(category)
    if isinstance(rule, dict) and level >= settings["decline_threshold"]:
        allowed = not rule.get("hydrogen") or hydrogen_relation(result, candidate)
        if rule["action"] == "reject" and result["recommendation"] != "reject":
            allowed = False
        if allowed:
            return rule["action"]
    if result["recommendation"] == "accept" and category == "v_rozsahu":
        return "propose" if level >= settings["accept_threshold"] and result.get("scope_areas") else "recommend"
    return "recommend"


# --- one decision --------------------------------------------------------------------

Decision = collections.namedtuple("Decision", "candidate_id rule action note metadata areas model errors")


def decide(candidate, config, index, document_types, cur=None, assessor=None, linked=None, sources=None,
           rules_only=False):
    """The Decision for one candidate (a dict of a `DocumentCandidate` row with `evidence`
    parsed). `cur` validates a proposal against the database; without it only the fields
    are checked."""
    rule = match_rule(candidate, config, index)
    action, note, model, metadata, areas, errors = rule["action"], rule.get("note", ""), None, None, [], []
    when = rule.get("when", {})
    if when.get("duplicate"):
        found = duplicate_of(candidate, index)
        note = f"{note} {found[1][0].upper()}{found[1][1:]}." if found else note
    if when.get("language_variant"):
        others = language_variant_of(candidate, index)
        note = (f"{note} V databázi je v jiném jazyce: "
                + ", ".join(f"#{i} {identifier} ({language})" for i, identifier, language in others) + ".")
    if when.get("validity_status") and "zrušený" in when["validity_status"]:
        successors = repealing_acts(candidate, index)
        note = f"{note} Zrušil jej: {', '.join(successors)}." if successors else f"{note} Zrušující předpis neznáme."
    if action == "propose":
        metadata, areas = proposal_metadata(candidate, rule, config, index=index)
        if not areas:  # without a subject area the proposal would not pass; the model decides
            action, note = "model", f"{note} Věcný okruh z pravidla nevyplývá, rozhoduje model."
    if action == "model":
        if rules_only or assessor is None:
            return Decision(candidate["id"], rule["id"], "model", note, None, [], None, [])
        payload = build_payload(candidate, linked or {}, sources)
        model = assessor.assess(payload)
        if model is None:
            return Decision(candidate["id"], rule["id"], "recommend", "Model neodpověděl; rozhodují editoři.",
                            None, [], None, [])
        action = model_action(model, config, candidate)
        relation = "ano" if hydrogen_relation(model, candidate) else "ne"
        category, from_pattern = effective_category(model, candidate, config)
        shown = f"{category} (podle názvu; model: {model['category']})" \
            if from_pattern and category != model["category"] else category
        note = (f"Model ({assessor.model}): {RECOMMENDATION_LABELS[model['recommendation']]}, "
                f"jistota {confidence(model):.2f}, kategorie {shown}, vztah k vodíku {relation}. "
                f"{model['reasoning']}")
        if action == "propose":
            metadata, areas = proposal_metadata(candidate, None, config, model)
    if action == "propose":
        metadata["decision_note"] = f"Automat ({rule['id']}): {note}"[:1000]
        if cur is not None:
            metadata, errors = cd.validate_proposal(cur, metadata, areas, document_types)
        else:
            metadata, errors = _validate_offline(metadata, areas, document_types)
        if errors:
            action = "recommend"
    return Decision(candidate["id"], rule["id"], action, note, metadata, areas, model, errors)


class _NoDatabase:
    def execute(self, *args):
        pass

    def fetchone(self):
        return None


def _validate_offline(metadata, areas, document_types):
    return cd.validate_proposal(_NoDatabase(), metadata, areas, document_types)


# --- writing ---------------------------------------------------------------------------

def add_successors(cur, candidate, index):
    """Puts into the queue, as candidates of the source `validity`, the acts that repealed
    a repealed candidate (rule R8) and that are neither in the database nor in the queue;
    made without the network (candidates.successor_candidate). Returns their keys."""
    added = []
    for key in repealing_acts(candidate, index):
        if key.split(":", 1)[0] not in ("CZ", "EU") or index["keys"].get(key):
            continue
        cur.execute("SELECT id FROM DocumentCandidate WHERE candidate_key = %s", (key,))
        if cur.fetchone() is None:
            cd.upsert(cur, cd.successor_candidate(key, candidate.get("candidate_key"), index.get("validity") or {}))
            added.append(key)
    return added


def store(cur, candidate, decision, automat, act=True, index=None):
    """Writes the decision: the triage columns always, the action (proposal, rejection,
    deferral) only for a candidate still `new` that the automat has not acted on before
    (one an editor reopened stays with the editors) and when `act`. Returns the action
    taken ("propose", "reject", "defer" or "recommend")."""
    previous = _json(candidate.get("triage_json"))
    acted_before = bool(previous.get("applied_action"))
    action = decision.action if decision.action in ("propose", "reject", "defer") else "recommend"
    if not act or candidate["status"] != "new" or acted_before:
        action = "recommend"
    model = decision.model or {}
    record = {"rule": decision.rule, "action": decision.action, "note": decision.note, "at": _now(),
              "model": model or None, "errors": decision.errors or None,
              "proposal": ({k: decision.metadata.get(k) for k in ("document_type", "puvodce", "language",
                                                                    "jurisdikce", "scope_areas")}
                           if decision.metadata else None)}
    if action != "recommend":
        record["applied_action"] = action
    elif acted_before:
        record["applied_action"] = previous["applied_action"]
    recommendation = model.get("recommendation") or {"propose": "accept"}.get(decision.action, decision.action)
    if recommendation not in RECOMMENDATIONS:
        recommendation = None
    cur.execute("""UPDATE DocumentCandidate SET triage_rule = %s, triage_recommendation = %s,
                       triage_confidence = %s, triage_json = %s, triaged_at = NOW() WHERE id = %s""",
                (decision.rule, recommendation, confidence(model) if model else None, json.dumps(record, ensure_ascii=False),
                 candidate["id"]))
    trail = {"automat": True, "rule": decision.rule, "note": decision.note,
             "model": ({k: model.get(k) for k in ("recommendation", "confidence", "token_confidence", "category")}
                       if model else None)}
    if action == "propose" and index is not None and candidate.get("validity_status") == "zrušený":
        record["successors_added"] = add_successors(cur, candidate, index) or None
        cur.execute("UPDATE DocumentCandidate SET triage_json = %s WHERE id = %s",
                    (json.dumps(record, ensure_ascii=False), candidate["id"]))
    if action == "propose":
        cd.store_proposal(cur, candidate["id"], decision.metadata, automat)
        cd.audit(cur, candidate["id"], "PROPOSE", {"status": candidate["status"]},
                 {"status": "proposed", **decision.metadata, **trail}, automat)
    elif action in ("reject", "defer"):
        status = "rejected" if action == "reject" else "deferred"
        note = f"Automat ({decision.rule}): {decision.note}"[:1000]
        cd.store_decision(cur, candidate["id"], status, note, automat)
        cd.audit(cur, candidate["id"], action.upper(), {"status": candidate["status"]},
                 {"status": status, "note": note, **trail}, automat)
    return action


def _json(raw):
    try:
        return json.loads(raw) if raw else {}
    except ValueError:
        return {}


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# --- reading the queue ------------------------------------------------------------------

def load_queue(cur, ids=None):
    """The candidates the triage looks at: every `new` one (or those of `ids`), with
    `evidence` parsed."""
    cur.execute("SHOW COLUMNS FROM DocumentCandidate LIKE 'triage_json'")
    has_triage = cur.fetchone() is not None
    query = "SELECT * FROM DocumentCandidate WHERE status = 'new'"
    params = []
    if ids:
        query += " AND id IN (" + ",".join(["%s"] * len(ids)) + ")"
        params = list(ids)
    cur.execute(query + " ORDER BY id", params)
    rows = []
    for row in cur.fetchall():
        row = dict(row)
        row["evidence"] = _json(row.get("evidence_json"))
        if not has_triage:
            row["triage_json"] = None
        rows.append(row)
    return rows


def load_document_areas(cur):
    """{document id: [subject area]} from the source categories that name a subject area
    (SourceCategory, or Keyword before migrate_vocabulary.py; vocabulary.py)."""
    names = {name: n for n, name in cd.SCOPE_AREAS.items()}
    cat = vocabulary.category_tables(cur)
    if cat is None:
        return {}
    cur.execute(f"SELECT dc.document_id, c.{cat.name} AS name FROM {cat.link} dc JOIN {cat.table} c "
                f"ON c.id = dc.{cat.fk} WHERE c.{cat.name} IN (" + ",".join(["%s"] * len(names)) + ")", list(names))
    areas = collections.defaultdict(set)
    for row in cur.fetchall():
        areas[row["document_id"]].add(names[row["name"]])
    return {k: sorted(v) for k, v in areas.items()}


def load_documents(cur):
    cur.execute("SELECT id, identifier, title, language FROM Document")
    return [(r["id"], r["identifier"], r["title"], r["language"]) for r in cur.fetchall()]


def linked_documents(cur, candidates):
    """{id: (identifier, title)} of the documents of the database the candidates' evidence names."""
    ids = set()
    for c in candidates:
        evidence = c["evidence"]
        ids |= set((evidence.get("citing_ids") or [])[:5]) | set(evidence.get("amends_ids") or []) \
            | set(evidence.get("repeals_ids") or [])
    if not ids:
        return {}
    cur.execute("SELECT id, identifier, title FROM Document WHERE id IN (" + ",".join(["%s"] * len(ids)) + ")",
                sorted(ids))
    return {r["id"]: (r["identifier"], r["title"]) for r in cur.fetchall()}
