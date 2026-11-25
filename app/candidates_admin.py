"""Editor pages for candidates of new documents (`DocumentCandidate`,
src/tools/candidates.py): a list with filters, a detail with the evidence, and
the decisions.

* **Acceptance needs two editors**, like a correction (admin.py): one proposes it
  together with the metadata the document will get, a second, different editor
  confirms it (also enforced by the CHECK constraint `chk_dc_distinct_reviewers`).
  The confirmation creates the document in the database at once (with its first
  version, the subject area as a keyword and, for the act that repealed a document
  of the database, the `REPEALS` relation) and appends the record to
  data/accepted_candidates.json, which the pipeline reads, so the document survives
  a rebuild and its full text gets fetched (fetch_fulltext.py).
* **Rejecting and deferring need one editor**; both can be reopened.
* **A manual proposal** of a document creates a candidate already proposed by its
  author, waiting for a second editor.
* **Findings of monitored sources** (harvest_sources.py) are listed with the
  candidate, one per source; a candidate of the signal `draft` (a proposed act in
  the legislative process) becomes a document in the state `draft` (připravovaný),
  one of the signal `amendment` (a new amendment of documents of the database) gets
  the AMENDS relations to them.
* **The automat** (src/tools/triage.py, doc/FRONTA_AUTOMAT.md) may be the first proposer
  of an acceptance and may reject or defer by approved rules; it never signs in and never
  confirms. Its recommendations (rule, model, confidence, reasoning) are shown with every
  candidate, the list filters them, and an editor confirms, rejects or defers the ticked
  candidates at once (each one written to the AuditLog on its own).
* **Tiers** (doc/DATA_SOURCES.md odstavec 8.8): the list shows tier 1 by default (and
  candidates of the checks, which have none), tier 2 in a filter of its own, ordered
  by citations and then by the occurrences of the search term.

Every decision is written to the AuditLog (`table_name` = `DocumentCandidate`).
"""
import datetime
import json
import pathlib

from flask import abort, flash, redirect, render_template, request, session, url_for

from admin import REPO_ROOT, admin_bp, get_db, login_required
import areas as area_rules
import candidates as cd
import citation_closure as cc
import norm_editions
from triage import CATEGORIES, RECOMMENDATION_LABELS
import slug as slug_module

ACCEPTED_PATH = REPO_ROOT / "data" / "accepted_candidates.json"
# relations an acceptance creates that a rebuild must keep (load_document_relations.py reads the file), and
# the validity entry of a repealed act accepted from the MPO tables (document_states.py reads the cache)
EDITOR_RELATIONS_PATH = REPO_ROOT / "data" / "document_relations_editor.json"
VALIDITY_CACHE_PATH = REPO_ROOT / "data" / "validity_cache.json"
# `zdroj_dat` of an accepted document, in the database and in the pipeline's records alike, so that the
# full-text manifest key (`Kandidáti|<designation>|odkaz_hlavni`) matches the document's own source.
PIPELINE_SOURCE = "Kandidáti"
LANGUAGES = cd.LANGUAGES
STATE_LABELS = {"new": "nový", "proposed": "navržen k přijetí", "accepted": "přijat", "rejected": "zamítnut",
                "deferred": "odložen"}
# 1 = the candidate concerns the database directly, 2 = only indirectly (doc/DATA_SOURCES.md 8.9, 8.10)
TIERS = {"1": "Přímý vztah (pásmo 1)", "2": "Nepřímý vztah (pásmo 2)", "all": "oba vztahy"}
# the filter of what the automat did (doc/FRONTA_AUTOMAT.md)
AUTOMAT_FILTERS = {"": "vše (i bez automatu)", "navrhy": "návrhy automatu k potvrzení",
                   "rozhodnuti": "zamítnuté či odložené automatem", "doporuceni": "s doporučením modelu"}
RECOMMENDATION_FILTERS = {"": "jakékoli doporučení", "accept": "doporučení: přijmout",
                          "reject": "doporučení: zamítnout", "defer": "doporučení: odložit"}
CONFIDENCE_FILTERS = {"": "jakákoli jistota", "0.95": "jistota ≥ 0,95", "0.9": "jistota ≥ 0,90",
                      "0.7": "jistota ≥ 0,70"}
FILTER_STATES = {"open": cd.OPEN_STATES, "new": ("new",), "proposed": ("proposed",), "deferred": ("deferred",),
                 "accepted": ("accepted",), "rejected": ("rejected",), "all": cd.STATES}


def document_types(db):
    with db.cursor() as cur:
        # all types, standards too: a "Norma" is kept as metadata, fetch_fulltext.py never downloads its text
        cur.execute("SELECT name FROM DocumentType ORDER BY name")
        return [row["name"] for row in cur.fetchall()]


def fetch_candidate(db, candidate_id):
    with db.cursor() as cur:
        cur.execute("""
            SELECT c.*, pu.name AS proposed_by_name, pu.username AS proposed_by_username,
                   cu.name AS confirmed_by_name, du.name AS decided_by_name, d.slug AS document_slug,
                   pu.username = %s AS proposed_by_automat, du.username = %s AS decided_by_automat
            FROM DocumentCandidate c
            LEFT JOIN User pu ON pu.id = c.proposed_by_user_id
            LEFT JOIN User cu ON cu.id = c.confirmed_by_user_id
            LEFT JOIN User du ON du.id = c.decided_by_user_id
            LEFT JOIN Document d ON d.id = c.document_id
            WHERE c.id = %s""", (cd.AUTOMAT_USERNAME, cd.AUTOMAT_USERNAME, candidate_id))
        return cur.fetchone()


def has_triage(db):
    """Whether the table has the columns of the automatic triage (a database not yet
    migrated by triage_candidates.py --apply has not)."""
    with db.cursor() as cur:
        cur.execute("SHOW COLUMNS FROM DocumentCandidate LIKE 'triage_json'")
        return cur.fetchone() is not None


def triage_of(candidate):
    """The stored triage record of a candidate (dict), {} without one."""
    try:
        return json.loads(candidate.get("triage_json") or "{}")
    except ValueError:
        return {}


def audit(cur, candidate_id, action, old, new):
    cd.audit(cur, candidate_id, action, old, new, session["user_id"])


@admin_bp.route("/candidates")
@login_required
def candidate_list():
    db = get_db()
    state = request.args.get("stav", "open")
    states = FILTER_STATES.get(state, cd.OPEN_STATES)
    source = request.args.get("zdroj", "")
    sources = cd.source_labels()
    family = request.args.get("skupina", "")
    query = (request.args.get("q") or "").strip()
    tier = request.args.get("pasmo", "1")
    tier = tier if tier in TIERS else "1"
    automat = request.args.get("automat", "")
    automat = automat if automat in AUTOMAT_FILTERS else ""
    recommendation = request.args.get("doporuceni", "")
    recommendation = recommendation if recommendation in RECOMMENDATION_FILTERS else ""
    level = request.args.get("jistota", "")
    level = level if level in CONFIDENCE_FILTERS else ""
    triage_columns = has_triage(db)
    conditions = ["c.status IN (" + ",".join(["%s"] * len(states)) + ")"]
    params = list(states)
    if tier != "all" and not automat:  # the automat's work is listed in both tiers
        conditions.append("COALESCE(c.tier, 1) = %s")
        params.append(int(tier))
    if source in sources:
        conditions.append("c.source = %s")
        params.append(source)
    if family in ("CZ", "EU"):  # drafts have keys `DRAFT-CZ:…`, `DRAFT-EU:…`
        conditions.append("(c.candidate_key LIKE %s OR c.candidate_key LIKE %s)")
        params += [family + ":%", f"DRAFT-{family}:%"]
    if query:
        conditions.append("(c.title LIKE %s OR c.designation LIKE %s)")
        params += [f"%{query}%", f"%{query}%"]
    if automat == "navrhy":
        conditions.append("c.status = 'proposed' AND pu.username = %s")
        params.append(cd.AUTOMAT_USERNAME)
    elif automat == "rozhodnuti":
        conditions.append("c.status IN ('rejected', 'deferred') AND du.username = %s")
        params.append(cd.AUTOMAT_USERNAME)
    elif automat == "doporuceni" and triage_columns:
        conditions.append("c.triage_recommendation IS NOT NULL")
    if triage_columns and recommendation:
        conditions.append("c.triage_recommendation = %s")
        params.append(recommendation)
    if triage_columns and level:
        conditions.append("c.triage_confidence >= %s")
        params.append(float(level))
    with db.cursor() as cur:
        cur.execute(f"""SELECT c.*, pu.name AS proposed_by_name, pu.username = %s AS proposed_by_automat,
                               du.username = %s AS decided_by_automat
                        FROM DocumentCandidate c
                        LEFT JOIN User pu ON pu.id = c.proposed_by_user_id
                        LEFT JOIN User du ON du.id = c.decided_by_user_id
                        WHERE {' AND '.join(conditions)}
                        ORDER BY c.status = 'proposed' DESC, COALESCE(c.tier, 1), c.cited_by DESC,
                                 COALESCE(c.occurrences, 0) DESC, c.candidate_key LIMIT 1000""",
                    [cd.AUTOMAT_USERNAME, cd.AUTOMAT_USERNAME] + params)
        rows = cur.fetchall()
        cur.execute("SELECT COALESCE(tier, 1) AS tier, COUNT(*) AS n FROM DocumentCandidate WHERE status IN ("
                    + ",".join(["%s"] * len(states)) + ") GROUP BY COALESCE(tier, 1)", list(states))
        tier_counts = {str(row["tier"]): row["n"] for row in cur.fetchall()}
        cur.execute("SELECT status, COUNT(*) AS n FROM DocumentCandidate GROUP BY status")
        counts = {row["status"]: row["n"] for row in cur.fetchall()}
        cur.execute("""SELECT COUNT(*) AS n FROM DocumentCandidate c JOIN User u ON u.id = c.proposed_by_user_id
                       WHERE c.status = 'proposed' AND u.username = %s""", (cd.AUTOMAT_USERNAME,))
        automat_proposals = cur.fetchone()["n"]
    for row in rows:
        row["triage"] = triage_of(row)
    confirmable = any(r["status"] == "proposed" and r["proposed_by_user_id"] != session["user_id"] for r in rows)
    return render_template("admin/candidates_list.html", rows=rows, counts=counts, state=state, source=source,
                           family=family, query=query, sources=sources, state_labels=STATE_LABELS, tier=tier,
                           tiers=TIERS, tier_counts=tier_counts, automat=automat, automat_filters=AUTOMAT_FILTERS,
                           recommendation=recommendation, recommendation_filters=RECOMMENDATION_FILTERS,
                           level=level, confidence_filters=CONFIDENCE_FILTERS, triage_columns=triage_columns,
                           automat_proposals=automat_proposals, confirmable=confirmable,
                           recommendation_labels=RECOMMENDATION_LABELS)


def linked_documents(db, ids):
    if not ids:
        return []
    with db.cursor() as cur:
        cur.execute("SELECT id, slug, identifier, title FROM Document WHERE id IN ("
                    + ",".join(["%s"] * len(ids)) + ") ORDER BY identifier", list(ids))
        return cur.fetchall()


@admin_bp.route("/candidates/<int:candidate_id>")
@login_required
def candidate_detail(candidate_id):
    db = get_db()
    candidate = fetch_candidate(db, candidate_id)
    if candidate is None:
        abort(404)
    evidence = json.loads(candidate["evidence_json"] or "{}")
    triage = triage_of(candidate)
    form = dict(candidate)
    if candidate["status"] in ("new", "deferred"):  # the automat's proposal fills what the candidate lacks
        for field, value in ((triage.get("proposal") or {}) | _model_fields(triage)).items():
            if value and (not form.get(field) or (field == "document_type" and form[field] == "Nezařazeno")):
                form[field] = value
    return render_template("admin/candidate_detail.html", c=candidate, form=form, evidence=evidence, triage=triage,
                           recommendation_labels=RECOMMENDATION_LABELS, categories=CATEGORIES,
                           citing=linked_documents(db, evidence.get("citing_ids", [])[:50]),
                           repeals=linked_documents(db, evidence.get("repeals_ids", [])),
                           amends=linked_documents(db, evidence.get("amends_ids", [])),
                           types=document_types(db), languages=LANGUAGES, areas=cd.SCOPE_AREAS,
                           state_labels=STATE_LABELS, sources=cd.source_labels(),
                           findings=sorted(evidence.get("findings", {}).values(), key=lambda f: f.get("first_seen") or ""),
                           signal_labels=cd.SIGNAL_LABELS)


def _model_fields(triage):
    """The metadata the model suggested (official title, type, issuer, subject areas)."""
    model = triage.get("model") or {}
    fields = {"document_type": model.get("document_type"), "puvodce": model.get("puvodce")}
    if model.get("scope_areas") and model.get("recommendation") == "accept":
        fields["scope_areas"] = ",".join(str(n) for n in model["scope_areas"])
    return fields


def read_metadata(form, db, own_designation=None):
    """(metadata, errors) of the propose / manual forms; the same checks as the
    automat's proposals (candidates.validate_proposal)."""
    with db.cursor() as cur:
        return cd.validate_proposal(cur, form, form.getlist("scope_area"), document_types(db), own_designation)


def _store_proposal(cur, candidate_id, metadata):
    cd.store_proposal(cur, candidate_id, metadata, session["user_id"])


@admin_bp.route("/candidates/<int:candidate_id>/propose", methods=["POST"])
@login_required
def candidate_propose(candidate_id):
    db = get_db()
    candidate = fetch_candidate(db, candidate_id)
    if candidate is None:
        abort(404)
    if candidate["status"] not in ("new", "deferred"):
        flash("Kandidát už není otevřený k návrhu.", "error")
        return redirect(url_for("admin.candidate_detail", candidate_id=candidate_id))
    metadata, errors = read_metadata(request.form, db)
    if errors:
        for error in errors:
            flash(error, "error")
        return redirect(url_for("admin.candidate_detail", candidate_id=candidate_id))
    with db.cursor() as cur:
        _store_proposal(cur, candidate_id, metadata)
        audit(cur, candidate_id, "PROPOSE", {"status": candidate["status"]}, {"status": "proposed", **metadata})
    db.commit()
    flash("Přijetí navrženo — čeká na potvrzení jiným editorem.", "success")
    return redirect(url_for("admin.candidate_list"))


def _single_editor_decision(candidate_id, new_status, allowed, message, action):
    db = get_db()
    candidate = fetch_candidate(db, candidate_id)
    if candidate is None:
        abort(404)
    note = (request.form.get("decision_note") or "").strip()
    if candidate["status"] not in allowed:
        flash("Tento krok není v současném stavu kandidáta možný.", "error")
        return redirect(url_for("admin.candidate_detail", candidate_id=candidate_id))
    if new_status == "rejected" and not note:
        flash("Uveďte důvod zamítnutí.", "error")
        return redirect(url_for("admin.candidate_detail", candidate_id=candidate_id))
    with db.cursor() as cur:
        cd.store_decision(cur, candidate_id, new_status, note, session["user_id"])
        audit(cur, candidate_id, action, {"status": candidate["status"]}, {"status": new_status, "note": note})
    db.commit()
    flash(message, "success")
    return redirect(url_for("admin.candidate_list"))


@admin_bp.route("/candidates/<int:candidate_id>/reject", methods=["POST"])
@login_required
def candidate_reject(candidate_id):
    return _single_editor_decision(candidate_id, "rejected", ("new", "proposed", "deferred"),
                                   "Kandidát zamítnut.", "REJECT")


@admin_bp.route("/candidates/<int:candidate_id>/defer", methods=["POST"])
@login_required
def candidate_defer(candidate_id):
    return _single_editor_decision(candidate_id, "deferred", ("new", "proposed"), "Kandidát odložen.", "DEFER")


@admin_bp.route("/candidates/<int:candidate_id>/reopen", methods=["POST"])
@login_required
def candidate_reopen(candidate_id):
    return _single_editor_decision(candidate_id, "new", ("rejected", "deferred", "proposed"),
                                   "Kandidát znovu otevřen.", "REOPEN")


def unique_slug(cur, identifier, title):
    base = slug_module.base_slug(identifier, title)
    cur.execute("SELECT slug FROM Document WHERE slug = %s OR slug LIKE %s", (base, base + "-%"))
    taken = {row["slug"] for row in cur.fetchall()}
    if base not in taken:
        return base
    return next(f"{base}-{n}" for n in range(2, 10000) if f"{base}-{n}" not in taken)


def source_id(cur, name, jurisdikce=None):
    """The DocumentSource of the issuing institution `name`, created with the first
    document that has it (so the public filter never lists an institution without
    documents); None without a name."""
    if not name:
        return None
    cur.execute("SELECT id FROM DocumentSource WHERE name = %s", (name,))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute("INSERT INTO DocumentSource (name, jurisdiction) VALUES (%s, %s)", (name, jurisdikce or None))
    return cur.lastrowid


def create_document(cur, candidate):
    """Creates the document of an accepted candidate; returns its id."""
    cur.execute("SELECT id FROM DocumentType WHERE name = %s", (candidate["document_type"],))
    type_id = cur.fetchone()["id"]
    identifier = candidate["designation"] or None
    title = candidate["title"]
    cur.execute("""INSERT INTO Document (title, description, type_id, source_id, language, url, identifier,
                                         jurisdikce, needs_review, review_reason, zdroj_dat, slug)
                   VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, 1, 'chybí popis/anotace dokumentu', %s, %s)""",
                (title, type_id, source_id(cur, candidate.get("puvodce"), candidate["jurisdikce"]),
                 candidate["language"], candidate["url"], identifier, candidate["jurisdikce"], PIPELINE_SOURCE,
                 unique_slug(cur, identifier, title)))
    doc_id = cur.lastrowid
    if candidate.get("signal") == "draft":
        state = "draft"
    elif candidate.get("validity_status") == "zrušený":  # a repealed act is kept with its state (rule R8)
        state = "repealed"
    elif candidate.get("validity_status") == "dosud neúčinný":
        state = "promulgated"
    else:
        state = "active"
    evidence = json.loads(candidate["evidence_json"] or "{}")
    # a standard: the edition in force and one issued with a later date of effect (norm_editions.py)
    versions = norm_editions.candidate_versions(evidence, datetime.date.today().isoformat()) \
        if candidate["document_type"] == norm_editions.NORM_TYPE else None
    if versions:
        for version in versions:
            cur.execute("""INSERT INTO DocumentVersion (document_id, version, edition_label, effective_date,
                                                         is_current, lifecycle_state)
                           VALUES (%s, %s, %s, %s, %s, %s)""", (doc_id,) + version)
    else:
        cur.execute("""INSERT INTO DocumentVersion (document_id, version, is_current, lifecycle_state)
                       VALUES (%s, 1, 1, %s)""", (doc_id, state))
    for area in (cd.SCOPE_AREAS[n] for n in cd.scope_areas(candidate) if n in cd.SCOPE_AREAS):
        cur.execute("SELECT id FROM Keyword WHERE keyword = %s", (area,))
        row = cur.fetchone()
        if row is None:
            cur.execute("INSERT INTO Keyword (keyword) VALUES (%s)", (area,))
            keyword_id = cur.lastrowid
        else:
            keyword_id = row["id"]
        cur.execute("INSERT INTO DocumentKeyword (document_id, keyword_id) VALUES (%s, %s)", (doc_id, keyword_id))
    area_rules.assign_document(cur, doc_id)  # the areas of the catalogue (data/areas.json, doc/OBLASTI.md)
    for repealed in evidence.get("repeals_ids", []):
        cur.execute("""INSERT IGNORE INTO document_relation (from_document_id, to_document_id, relation_type, note)
                       VALUES (%s, %s, 'REPEALS', 'Zrušující předpis podle kontroly platnosti (přijatý kandidát).')""",
                    (doc_id, repealed))
    for amended in evidence.get("amends_ids", []):
        cur.execute("""INSERT IGNORE INTO document_relation (from_document_id, to_document_id, relation_type, note)
                       VALUES (%s, %s, 'AMENDS', 'Novela podle nálezu sledovaného zdroje (přijatý kandidát).')""",
                    (doc_id, amended))
    link_language_versions(cur, doc_id, identifier, candidate["language"])
    if state == "repealed":
        link_repealing_acts(cur, doc_id, candidate, evidence)
    return doc_id


def _relation_exists(cur, from_id, to_id, relation_type):
    cur.execute("SELECT id FROM document_relation WHERE from_document_id = %s AND to_document_id = %s "
                "AND relation_type = %s", (from_id, to_id, relation_type))
    return cur.fetchone() is not None


def save_relation(from_identifier, to_identifier, relation_type, note, path=None):
    """Appends a relation (load_document_relations.py shape, by identifier) to
    data/document_relations_editor.json once, so that a rebuild keeps it."""
    path = pathlib.Path(path or EDITOR_RELATIONS_PATH)
    relations = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    if not any((r["from_identifier"], r["to_identifier"], r["relation_type"]) ==
               (from_identifier, to_identifier, relation_type) for r in relations):
        relations.append({"from_identifier": from_identifier, "to_identifier": to_identifier,
                          "relation_type": relation_type, "note": note})
        path.write_text(json.dumps(relations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def link_language_versions(cur, doc_id, identifier, language):
    """`TRANSLATION_OF` between a new document and every other language version of the
    same act in the database (rule R7; the English or Slovak text points to the Czech
    one, language_variants.py), also written for a rebuild."""
    if not identifier:
        return []
    others = cd.same_act_documents(cur, identifier, exclude=doc_id)
    links = cd.translation_relations((doc_id, identifier, language), others)
    for (from_id, from_identifier, _), (to_id, to_identifier, _) in links:
        note = "Jazykové verze téhož předpisu (přijatý kandidát)."
        if not _relation_exists(cur, from_id, to_id, "TRANSLATION_OF"):
            cur.execute("""INSERT INTO document_relation (from_document_id, to_document_id, relation_type, note)
                           VALUES (%s, %s, 'TRANSLATION_OF', %s)""", (from_id, to_id, note))
        save_relation(from_identifier, to_identifier, "TRANSLATION_OF", note)
    return links


def link_repealing_acts(cur, doc_id, candidate, evidence):
    """For an accepted repealed act (rule R8): `REPEALS` from every act that repealed it
    and is in the database; an act still waiting in the queue gets the new document in
    its `repeals_ids`, so its acceptance creates the relation (create_document above).
    The validity entry of the act goes to data/validity_cache.json when the cache lacks
    it, so that a rebuild keeps the state and the relation (document_states.py)."""
    import document_states as ds
    cache = ds.load_cache(VALIDITY_CACHE_PATH)
    keys = cd.successors(candidate, evidence, cache)
    in_database = cd.documents_by_key(cur, keys)
    for key in keys:
        for successor_id, _ in in_database.get(key, []):
            if not _relation_exists(cur, successor_id, doc_id, "REPEALS"):
                cur.execute("""INSERT INTO document_relation (from_document_id, to_document_id, relation_type, note)
                               VALUES (%s, %s, 'REPEALS', 'Zrušující předpis (přijatý zrušený kandidát).')""",
                            (successor_id, doc_id))
        if key in in_database:
            continue
        cur.execute("SELECT id, evidence_json FROM DocumentCandidate WHERE candidate_key = %s AND status <> 'rejected'",
                    (key,))
        waiting = cur.fetchone()
        if waiting:
            other = json.loads(waiting["evidence_json"] or "{}")
            other["repeals_ids"] = sorted(set(other.get("repeals_ids", [])) | {doc_id})
            cur.execute("UPDATE DocumentCandidate SET evidence_json = %s WHERE id = %s",
                        (json.dumps(other, ensure_ascii=False), waiting["id"]))
    own = candidate.get("candidate_key") or ""
    validity = evidence.get("validity") or {}
    if own.split(":", 1)[0] in ("CZ", "EU") and own not in cache and validity.get("status") == "zrušený":
        cache[own] = {**validity, "checked_at": validity.get("checked_at") or datetime.date.today().isoformat()}
        # the format of check_validity.py, so that its next run changes only what it re-checks
        pathlib.Path(VALIDITY_CACHE_PATH).write_text(json.dumps(dict(sorted(cache.items())), ensure_ascii=False,
                                                                indent=1) + "\n", encoding="utf-8")
    return keys


def pipeline_record(candidate, confirmed_by):
    """The record of an accepted candidate in the shape of the pipeline's JSON
    (build_unified_db.py), keyed by the candidate key in data/accepted_candidates.json."""
    return {"zdroj_dat": PIPELINE_SOURCE, "znacka": candidate["designation"] or "", "nazev_cz": candidate["title"],
            "typ_dokumentu": candidate["document_type"], "sekce": "", "kategorie_trida": "",
            "klicova_slova": [cd.SCOPE_AREAS[n] for n in cd.scope_areas(candidate) if n in cd.SCOPE_AREAS],
            "odkaz_hlavni": candidate["url"] or "", "nazev_eu": "", "odkaz_eu": "", "nazev_sk": "", "odkaz_sk": "",
            "platnost": "", "ratifikovan": "", "gestor": [candidate["puvodce"]] if candidate.get("puvodce") else [],
            "jazyk": candidate["language"] or "",
            "anotace_poznamka": "", "jurisdikce": candidate["jurisdikce"] or "",
            "candidate_source": candidate["source"], "accepted_by": confirmed_by,
            "proposed_by": candidate.get("proposed_by_username")}


def save_accepted(key, record, path=None):
    path = pathlib.Path(path or ACCEPTED_PATH)
    accepted = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    accepted[key] = record
    path.write_text(json.dumps(accepted, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _confirm(cur, candidate, bulk=False):
    """Confirms a proposed candidate: creates its document and writes the AuditLog. The
    caller checks that the candidate is proposed and that the confirming editor is not
    its proposer; returns the new document's id."""
    doc_id = create_document(cur, candidate)
    cur.execute("""UPDATE DocumentCandidate SET status = 'accepted', confirmed_by_user_id = %s,
                       confirmed_at = NOW(), document_id = %s WHERE id = %s""",
                (session["user_id"], doc_id, candidate["id"]))
    audit(cur, candidate["id"], "CONFIRM", {"status": "proposed"},
          {"status": "accepted", "document_id": doc_id, **({"bulk": True} if bulk else {})})
    cur.execute("""INSERT INTO AuditLog (table_name, record_id, action, new_value_json, changed_by_user_id)
                   VALUES ('Document', %s, 'INSERT', %s, %s)""",
                (doc_id, json.dumps({"from_candidate": candidate["id"], "identifier": candidate["designation"],
                                     "title": candidate["title"]}, ensure_ascii=False), session["user_id"]))
    return doc_id


def _confirmable(candidate):
    return candidate["status"] == "proposed" and candidate["proposed_by_user_id"] != session["user_id"] \
        and session.get("username") != cd.AUTOMAT_USERNAME


@admin_bp.route("/candidates/<int:candidate_id>/confirm", methods=["POST"])
@login_required
def candidate_confirm(candidate_id):
    db = get_db()
    candidate = fetch_candidate(db, candidate_id)
    if candidate is None:
        abort(404)
    if candidate["status"] != "proposed":
        flash("Kandidát není navržen k přijetí.", "error")
        return redirect(url_for("admin.candidate_detail", candidate_id=candidate_id))
    if not _confirmable(candidate):
        abort(403)
    with db.cursor() as cur:
        _confirm(cur, candidate)
    db.commit()
    key = candidate["candidate_key"] or f"manual:{candidate_id}"
    save_accepted(key, pipeline_record(candidate, session.get("username")))
    flash("Kandidát přijat a dokument založen.", "success")
    return redirect(url_for("admin.candidate_detail", candidate_id=candidate_id))


BULK_ACTIONS = {"confirm": "potvrzeno přijetí", "defer": "odloženo", "reject": "zamítnuto"}


@admin_bp.route("/candidates/bulk", methods=["POST"])
@login_required
def candidate_bulk():
    """Confirms, defers or rejects the ticked candidates, each one on its own (its own
    checks, its own AuditLog record); a candidate that cannot take the step is skipped."""
    db = get_db()
    action = request.form.get("action")
    if action not in BULK_ACTIONS:
        abort(400)
    ids = sorted({int(i) for i in request.form.getlist("ids") if i.isdigit()})
    note = (request.form.get("decision_note") or "").strip()
    back = request.form.get("back") or url_for("admin.candidate_list")
    if not back.startswith(request.script_root + "/admin/candidates"):  # only back to the list, behind WSGI too
        back = url_for("admin.candidate_list")
    if not ids:
        flash("Nevybrali jste žádného kandidáta.", "error")
        return redirect(back)
    if action == "reject" and not note:
        flash("Uveďte důvod zamítnutí.", "error")
        return redirect(back)
    done, skipped = 0, []
    for candidate_id in ids:
        candidate = fetch_candidate(db, candidate_id)
        if candidate is None:
            continue
        label = candidate["designation"] or candidate["candidate_key"] or f"#{candidate_id}"
        if action == "confirm":
            if not _confirmable(candidate):
                skipped.append(label)
                continue
            with db.cursor() as cur:
                _confirm(cur, candidate, bulk=True)
            db.commit()
            save_accepted(candidate["candidate_key"] or f"manual:{candidate_id}",
                          pipeline_record(candidate, session.get("username")))
        else:
            allowed = ("new", "proposed", "deferred") if action == "reject" else ("new", "proposed")
            if candidate["status"] not in allowed:
                skipped.append(label)
                continue
            new_status = "rejected" if action == "reject" else "deferred"
            with db.cursor() as cur:
                cd.store_decision(cur, candidate_id, new_status, note, session["user_id"])
                audit(cur, candidate_id, action.upper(), {"status": candidate["status"]},
                      {"status": new_status, "note": note, "bulk": True})
            db.commit()
        done += 1
    flash(f"Hromadně {BULK_ACTIONS[action]}: {done}." + (f" Přeskočeno (stav to nedovoluje nebo jde o vlastní návrh): "
                                                         f"{', '.join(skipped[:10])}{' …' if len(skipped) > 10 else ''}."
                                                         if skipped else ""), "success" if done else "error")
    return redirect(back)


@admin_bp.route("/candidates/new", methods=["GET", "POST"])
@login_required
def candidate_new():
    db = get_db()
    if request.method == "GET":
        return render_template("admin/candidate_new.html", types=document_types(db), languages=LANGUAGES,
                               areas=cd.SCOPE_AREAS, form={})
    metadata, errors = read_metadata(request.form, db)
    key = None
    if metadata["designation"]:
        keys = sorted(cc.own_keys(metadata["designation"], metadata["title"]))
        key = keys[0] if keys else None
    if key:
        with db.cursor() as cur:
            cur.execute("SELECT id FROM DocumentCandidate WHERE candidate_key = %s", (key,))
            existing = cur.fetchone()
        if existing:
            flash("Tento dokument už je mezi kandidáty.", "error")
            return redirect(url_for("admin.candidate_detail", candidate_id=existing["id"]))
    if errors:
        for error in errors:
            flash(error, "error")
        return render_template("admin/candidate_new.html", types=document_types(db), languages=LANGUAGES,
                               areas=cd.SCOPE_AREAS, form={**request.form.to_dict(),  # every area ticked
                                                           "scope_areas": ",".join(request.form.getlist("scope_area"))})
    with db.cursor() as cur:
        cur.execute("""INSERT INTO DocumentCandidate (candidate_key, source, evidence_json) VALUES (%s, 'manual', %s)""",
                    (key, json.dumps({"proposed_manually": True}, ensure_ascii=False)))
        candidate_id = cur.lastrowid
        _store_proposal(cur, candidate_id, metadata)
        audit(cur, candidate_id, "PROPOSE", {}, {"status": "proposed", "manual": True, **metadata})
    db.commit()
    flash("Návrh dokumentu uložen — čeká na potvrzení jiným editorem.", "success")
    return redirect(url_for("admin.candidate_list"))
