"""The common parts of harvesting the monitored sources (doc/DATA_SOURCES.md,
odstavec 4.2): the shape of a finding, its way into the candidate queue, and the
log of every run.

* A **finding** (Finding) is what an adapter of a source returns for one document:
  the source, the kind of signal, the candidate key when it can be derived
  (`CZ:N/RRRR`, `EU:RRRR/N`, ...), designation, title, address, date and a verbatim
  excerpt as evidence. A finding without a derivable key gets a key of its own
  (`<source>:<native id>`) and the flag `needs_key`, never a guessed key.
* **Writing** (write_findings) turns findings of the signals `new_document` and
  `draft` into candidates (candidates.upsert_finding); a document the database
  already has (by key, or by address for documents without a designation) is
  counted as `known` and not written. `state_change` findings carry the state a
  check found (`state`) and go to the cache of that check (apply_state_changes):
  Czech and EU acts to data/validity_cache.json, which backfill_document_states.py
  applies to the database, standards to data/norm_validity_cache.json.
  An `amendment` finding (a new amending act of a document the database has) is a
  candidate too, carrying the ids of the amended documents (`amends_ids`), so that
  accepting it creates the AMENDS relation. An `excluded` finding is not queued but
  written, with its reason, to data/harvest_not_imported.json (record_excluded): what a
  source found and a filter left out stays visible (doc/DATA_SOURCES.md, odstavec 8.8).
* A candidate gets the **tier** of its finding (1 shown by default, 2 in a filter of
  its own) and the number of **occurrences** of the search term, by which the queue
  is ordered.
* The **log** (data/source_checks.jsonl, one JSON object per line) records every
  run of a source and every availability check, also those that found nothing:
  the documented negative results of doc/DATABASE_SCOPE.md, odstavec 6.
"""
import collections
import dataclasses
import datetime
import hashlib
import json
import pathlib
import re

import candidates as cd
import citation_closure as cc

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
LOG_PATH = REPO_ROOT / "data" / "source_checks.jsonl"
VALIDITY_CACHE_PATH = REPO_ROOT / "data" / "validity_cache.json"
NORM_CACHE_PATH = REPO_ROOT / "data" / "norm_validity_cache.json"
NOT_IMPORTED_PATH = REPO_ROOT / "data" / "harvest_not_imported.json"
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-harvest/1.0; +research use, low-volume)"
QUEUED_SIGNALS = ("new_document", "draft", "amendment")

# Search terms of doc/DATA_SOURCES.md odstavec 6: the basic terms on their own mark a
# finding as relevant; the broader areas are to be combined with a process or an act.
BASIC_TERMS = ("vodík", "elektrolyzér", "elektrolýz", "palivový článek", "palivové články", "plnicí stanic",
               "hydrogen", "electroly", "fuel cell", "refuelling station", "refueling station",
               "wasserstoff", "elektrolyseur", "brennstoffzelle", "wasserstofftankstelle")
BROADER_TERMS = ("tlaková zařízení", "tlakových zařízení", "plynová zařízení", "hořlavý plyn", "hořlavých plynů",
                 "atex", "ochrana před výbuchem", "výbušn", "vyhrazená technická zařízení",
                 "přeprava nebezpečných věcí", "metrologi", "jakost paliv", "jakosti paliv",
                 "pressure equipment", "explosive atmosphere", "dangerous goods", "hydrogen purity", "fuel quality",
                 "conformity assessment", "rfnbo", "low-carbon hydrogen",
                 "druckgeräte", "explosionsschutz", "gefahrgut", "genehmigungsverfahren")
# Words that begin like a basic term but are something else (hydrogenerators: hydro-electric generators).
NOT_TERMS = ("hydrogenerat",)
# Standards and technical rules whose designation citation_closure.own_keys() does not read
# (national ČSN, TPG, SAE, …): their key is `NORM:` with the designation itself.
NATIONAL_STANDARD = re.compile(r"^(ČSN|STN|TPG|TDG|TIN|SAE|ASME|ASTM|DVGW|NFPA|API)\b")


@dataclasses.dataclass
class Finding:
    source: str
    signal: str
    title: str
    url: str = None
    key: str = None
    native_id: str = None
    designation: str = None
    document_type: str = None
    language: str = None
    jurisdikce: str = None
    date: str = None
    excerpt: str = None
    state: dict = None
    tier: int = None
    occurrences: int = None
    extra: dict = None

    def candidate_key(self):
        if self.key:
            return self.key
        native = self.native_id or hashlib.sha256((self.url or self.title).encode("utf-8")).hexdigest()[:12]
        return f"{self.source}:{native}"[:120]

    def as_candidate(self):
        return {"candidate_key": self.candidate_key(), "designation": self.designation, "title": self.title,
                "document_type": self.document_type, "url": self.url, "language": self.language,
                "jurisdikce": self.jurisdikce, "tier": self.tier, "occurrences": self.occurrences}

    def as_evidence(self, seen):
        evidence = {"source": self.source, "signal": self.signal, "title": self.title, "url": self.url,
                    "date": self.date, "excerpt": self.excerpt, "seen": seen}
        if not self.key:
            evidence["needs_key"] = True
        return {**evidence, **(self.extra or {})}


def matches(text, broader=False):
    """Whether `text` contains a basic search term (or, with `broader`, also a term of
    the broader areas). Case-insensitive; terms are word beginnings."""
    lowered = (text or "").lower()
    for word in NOT_TERMS:
        lowered = lowered.replace(word, " ")
    terms = BASIC_TERMS + (BROADER_TERMS if broader else ())
    return any(re.search(r"(?<!\w)" + re.escape(term), lowered) for term in terms)


def norm_key(designation):
    """The key of a standard: what own_keys() reads (`ČSN EN 17124` → `NORM:EN 17124`),
    else `NORM:<designation>` for a national designation, else None."""
    text = " ".join((designation or "").split())
    if not text:
        return None
    keys = sorted(k for k in cc.own_keys(text, "") if k.startswith("NORM:"))
    if keys:
        return keys[0]
    return f"NORM:{text}" if NATIONAL_STANDARD.match(text) else None


def documents(cursor):
    """[(id, identifier, title, url)] of the documents of the database."""
    cursor.execute("SELECT id, identifier, title, url FROM Document")
    return [(r["id"], r["identifier"], r["title"], r["url"]) if isinstance(r, dict) else tuple(r[:4])
            for r in cursor.fetchall()]


def known_keys(cursor_or_documents):
    """What the database already has: the candidate keys of its documents and
    `url:<address>` of every document address (for documents without a
    designation, such as strategies and studies)."""
    docs = cursor_or_documents if isinstance(cursor_or_documents, list) else documents(cursor_or_documents)
    keys = set()
    for _doc_id, identifier, title, url in docs:
        keys |= cc.own_keys(identifier, title)
        national = norm_key(identifier) if identifier and NATIONAL_STANDARD.match(identifier.strip()) else None
        if national:
            keys.add(national)
        if url:
            keys.add("url:" + url.strip())
    return keys


def write_findings(cursor, findings, known, seen):
    """Writes the findings into the candidate queue; returns a Counter of outcomes
    (inserted, updated, kept, known, state_change, excluded, not_queued)."""
    outcome = collections.Counter()
    for finding in findings:
        if finding.signal in ("state_change", "excluded"):
            outcome[finding.signal] += 1
        elif finding.signal not in QUEUED_SIGNALS:
            outcome["not_queued"] += 1
        elif (finding.key and finding.key in known) or (finding.url and "url:" + finding.url.strip() in known):
            outcome["known"] += 1
        else:
            outcome[cd.upsert_finding(cursor, finding.as_candidate(), finding.as_evidence(seen))] += 1
    return outcome


def apply_state_changes(findings, today, validity_path=None, norm_path=None):
    """Writes the `state` of state_change findings into the cache of their check
    (`checked_at` = today); returns a Counter (state_changed, state_unchanged).
    A finding's key decides the cache: `CZ:`/`EU:` the validity cache, any other
    the standards cache."""
    paths = {"validity": pathlib.Path(validity_path or VALIDITY_CACHE_PATH),
             "norm": pathlib.Path(norm_path or NORM_CACHE_PATH)}
    caches = {name: (json.loads(path.read_text(encoding="utf-8")) if path.exists() else {})
              for name, path in paths.items()}
    outcome, touched = collections.Counter(), set()
    for finding in findings:
        if finding.signal != "state_change" or not finding.key or finding.state is None:
            continue
        name = "validity" if finding.key.split(":")[0] in ("CZ", "EU") else "norm"
        cache = caches[name]
        old = cache.get(finding.key, {})
        # A standard is described by several sources (catalogue, Věstník, harmonised lists, TPG): merged.
        cache[finding.key] = {**(old if name == "norm" else {}), **finding.state, "checked_at": today}
        touched.add(name)
        changed = "status" in finding.state and old.get("status") != finding.state["status"]
        outcome["state_changed" if changed or not old else "state_unchanged"] += 1
    for name in touched:
        paths[name].write_text(json.dumps(dict(sorted(caches[name].items())), ensure_ascii=False, indent=1) + "\n",
                               encoding="utf-8")
    return outcome


def record_excluded(findings, seen, path=None):
    """Writes the `excluded` findings to the not-imported file — {source: {key:
    {title, url, reason, first_seen, seen}}} — and returns how many there were."""
    path = pathlib.Path(path or NOT_IMPORTED_PATH)
    excluded = [f for f in findings if f.signal == "excluded"]
    if not excluded:
        return 0
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for finding in excluded:
        entries = data.setdefault(finding.source, {})
        key = finding.candidate_key()
        entries[key] = {"title": finding.title, "url": finding.url, "reason": (finding.extra or {}).get("reason"),
                        "first_seen": entries.get(key, {}).get("first_seen", seen), "seen": seen}
    path.write_text(json.dumps({s: dict(sorted(e.items())) for s, e in sorted(data.items())}, ensure_ascii=False,
                               indent=1) + "\n", encoding="utf-8")
    return len(excluded)


# --- the log of runs ----------------------------------------------------------

def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def log_run(record, path=None):
    """Appends a record (a dict with at least `kind` and `source`) to the log."""
    path = pathlib.Path(path or LOG_PATH)
    record = {"at": now(), **record}
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def read_log(path=None):
    path = pathlib.Path(path or LOG_PATH)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def last_runs(records, kind="harvest", successful=True):
    """{source: the latest record of `kind`}, by default only runs without an error
    that were applied (a dry run does not move the point an adapter continues from)."""
    latest = {}
    for record in records:
        if record.get("kind") != kind:
            continue
        if successful and (record.get("error") or not record.get("applied", True)):
            continue
        latest[record["source"]] = record
    return latest


def connect(env_file=None):
    """A DictCursor connection to the database of `env_file` (default `.env`)."""
    import pymysql
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(env_file or str(testdb.find_env_file(".env")))
    return pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"],
                           cursorclass=pymysql.cursors.DictCursor), env["DB_NAME"]
