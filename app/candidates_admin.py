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

Every decision is written to the AuditLog (`table_name` = `DocumentCandidate`).
"""
import json
import pathlib

from flask import abort, flash, redirect, render_template, request, session, url_for

from admin import REPO_ROOT, admin_bp, get_db, login_required
import candidates as cd
import citation_closure as cc
import slug as slug_module

ACCEPTED_PATH = REPO_ROOT / "data" / "accepted_candidates.json"
# `zdroj_dat` of an accepted document, in the database and in the pipeline's records alike, so that the
# full-text manifest key (`Kandidáti|<designation>|odkaz_hlavni`) matches the document's own source.
PIPELINE_SOURCE = "Kandidáti"
LANGUAGES = ("CS", "EN", "SK", "DE")
STATE_LABELS = {"new": "nový", "proposed": "navržen k přijetí", "accepted": "přijat", "rejected": "zamítnut",
                "deferred": "odložen"}
FILTER_STATES = {"open": cd.OPEN_STATES, "new": ("new",), "proposed": ("proposed",), "deferred": ("deferred",),
                 "accepted": ("accepted",), "rejected": ("rejected",), "all": cd.STATES}


def document_types(db):
    with db.cursor() as cur:
        cur.execute("SELECT name FROM DocumentType WHERE restricted_fulltext = 0 ORDER BY name")
        return [row["name"] for row in cur.fetchall()]


def fetch_candidate(db, candidate_id):
    with db.cursor() as cur:
        cur.execute("""
            SELECT c.*, pu.name AS proposed_by_name, pu.username AS proposed_by_username,
                   cu.name AS confirmed_by_name, du.name AS decided_by_name, d.slug AS document_slug
            FROM DocumentCandidate c
            LEFT JOIN User pu ON pu.id = c.proposed_by_user_id
            LEFT JOIN User cu ON cu.id = c.confirmed_by_user_id
            LEFT JOIN User du ON du.id = c.decided_by_user_id
            LEFT JOIN Document d ON d.id = c.document_id
            WHERE c.id = %s""", (candidate_id,))
        return cur.fetchone()


def audit(cur, candidate_id, action, old, new):
    cur.execute("""INSERT INTO AuditLog (table_name, record_id, action, old_value_json, new_value_json,
                                         changed_by_user_id)
                   VALUES ('DocumentCandidate', %s, %s, %s, %s, %s)""",
                (candidate_id, action, json.dumps(old, ensure_ascii=False, default=str),
                 json.dumps(new, ensure_ascii=False, default=str), session["user_id"]))


@admin_bp.route("/candidates")
@login_required
def candidate_list():
    db = get_db()
    state = request.args.get("stav", "open")
    states = FILTER_STATES.get(state, cd.OPEN_STATES)
    source = request.args.get("zdroj", "")
    family = request.args.get("skupina", "")
    query = (request.args.get("q") or "").strip()
    conditions = ["c.status IN (" + ",".join(["%s"] * len(states)) + ")"]
    params = list(states)
    if source in cd.SOURCES:
        conditions.append("c.source = %s")
        params.append(source)
    if family in ("CZ", "EU"):
        conditions.append("c.candidate_key LIKE %s")
        params.append(family + ":%")
    if query:
        conditions.append("(c.title LIKE %s OR c.designation LIKE %s)")
        params += [f"%{query}%", f"%{query}%"]
    with db.cursor() as cur:
        cur.execute(f"""SELECT c.*, pu.name AS proposed_by_name FROM DocumentCandidate c
                        LEFT JOIN User pu ON pu.id = c.proposed_by_user_id
                        WHERE {' AND '.join(conditions)}
                        ORDER BY c.status = 'proposed' DESC, c.cited_by DESC, c.candidate_key LIMIT 1000""", params)
        rows = cur.fetchall()
        cur.execute("SELECT status, COUNT(*) AS n FROM DocumentCandidate GROUP BY status")
        counts = {row["status"]: row["n"] for row in cur.fetchall()}
    return render_template("admin/candidates_list.html", rows=rows, counts=counts, state=state, source=source,
                           family=family, query=query, sources=cd.SOURCES, state_labels=STATE_LABELS)


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
    return render_template("admin/candidate_detail.html", c=candidate, evidence=evidence,
                           citing=linked_documents(db, evidence.get("citing_ids", [])[:50]),
                           repeals=linked_documents(db, evidence.get("repeals_ids", [])),
                           types=document_types(db), languages=LANGUAGES, areas=cd.SCOPE_AREAS,
                           state_labels=STATE_LABELS, sources=cd.SOURCES)


def read_metadata(form, db, own_designation=None):
    """(metadata, errors) of the propose / manual forms."""
    metadata = {field: (form.get(field) or "").strip() for field in
                ("designation", "title", "document_type", "url", "language", "jurisdikce", "decision_note")}
    errors = []
    if not metadata["title"]:
        errors.append("Název je povinný.")
    if metadata["document_type"] not in document_types(db):
        errors.append("Vyberte typ dokumentu.")
    if metadata["language"] not in LANGUAGES:
        errors.append("Vyberte jazyk.")
    try:
        metadata["scope_area"] = int(form.get("scope_area") or 0)
    except ValueError:
        metadata["scope_area"] = 0
    if metadata["scope_area"] not in cd.SCOPE_AREAS:
        errors.append("Vyberte věcný okruh (DATABASE_SCOPE.md, odstavec 3).")
    if metadata["designation"] and metadata["designation"] != own_designation:
        with db.cursor() as cur:
            cur.execute("SELECT id FROM Document WHERE identifier = %s", (metadata["designation"],))
            if cur.fetchone():
                errors.append(f"Dokument s označením {metadata['designation']} už v databázi je.")
    return metadata, errors


def _store_proposal(cur, candidate_id, metadata):
    cur.execute("""UPDATE DocumentCandidate SET designation = %s, title = %s, document_type = %s, url = %s,
                       language = %s, jurisdikce = %s, scope_area = %s, decision_note = %s, status = 'proposed',
                       proposed_by_user_id = %s, proposed_at = NOW(), confirmed_by_user_id = NULL,
                       confirmed_at = NULL
                   WHERE id = %s""",
                (metadata["designation"] or None, metadata["title"], metadata["document_type"],
                 metadata["url"] or None, metadata["language"], metadata["jurisdikce"] or None,
                 metadata["scope_area"], metadata["decision_note"] or None, session["user_id"], candidate_id))


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
        cur.execute("""UPDATE DocumentCandidate SET status = %s, decision_note = %s, decided_by_user_id = %s,
                           decided_at = NOW(), proposed_by_user_id = IF(%s = 'new', NULL, proposed_by_user_id)
                       WHERE id = %s""", (new_status, note or None, session["user_id"], new_status, candidate_id))
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


def create_document(cur, candidate):
    """Creates the document of an accepted candidate; returns its id."""
    cur.execute("SELECT id FROM DocumentType WHERE name = %s", (candidate["document_type"],))
    type_id = cur.fetchone()["id"]
    identifier = candidate["designation"] or None
    title = candidate["title"]
    cur.execute("""INSERT INTO Document (title, description, type_id, language, url, identifier, jurisdikce,
                                         needs_review, review_reason, zdroj_dat, slug)
                   VALUES (%s, NULL, %s, %s, %s, %s, %s, 1, 'chybí popis/anotace dokumentu', %s, %s)""",
                (title, type_id, candidate["language"], candidate["url"], identifier, candidate["jurisdikce"],
                 PIPELINE_SOURCE,
                 unique_slug(cur, identifier, title)))
    doc_id = cur.lastrowid
    state = "promulgated" if candidate.get("validity_status") == "dosud neúčinný" else "active"
    cur.execute("""INSERT INTO DocumentVersion (document_id, version, is_current, lifecycle_state)
                   VALUES (%s, 1, 1, %s)""", (doc_id, state))
    area = cd.SCOPE_AREAS.get(candidate["scope_area"])
    if area:
        cur.execute("SELECT id FROM Keyword WHERE keyword = %s", (area,))
        row = cur.fetchone()
        if row is None:
            cur.execute("INSERT INTO Keyword (keyword) VALUES (%s)", (area,))
            keyword_id = cur.lastrowid
        else:
            keyword_id = row["id"]
        cur.execute("INSERT INTO DocumentKeyword (document_id, keyword_id) VALUES (%s, %s)", (doc_id, keyword_id))
    evidence = json.loads(candidate["evidence_json"] or "{}")
    for repealed in evidence.get("repeals_ids", []):
        cur.execute("""INSERT IGNORE INTO document_relation (from_document_id, to_document_id, relation_type, note)
                       VALUES (%s, %s, 'REPEALS', 'Zrušující předpis podle kontroly platnosti (přijatý kandidát).')""",
                    (doc_id, repealed))
    return doc_id


def pipeline_record(candidate, confirmed_by):
    """The record of an accepted candidate in the shape of the pipeline's JSON
    (build_unified_db.py), keyed by the candidate key in data/accepted_candidates.json."""
    return {"zdroj_dat": PIPELINE_SOURCE, "znacka": candidate["designation"] or "", "nazev_cz": candidate["title"],
            "typ_dokumentu": candidate["document_type"], "sekce": "", "kategorie_trida": "",
            "klicova_slova": [cd.SCOPE_AREAS[candidate["scope_area"]]] if candidate["scope_area"] else [],
            "odkaz_hlavni": candidate["url"] or "", "nazev_eu": "", "odkaz_eu": "", "nazev_sk": "", "odkaz_sk": "",
            "platnost": "", "ratifikovan": "", "gestor": [], "jazyk": candidate["language"] or "",
            "anotace_poznamka": "", "jurisdikce": candidate["jurisdikce"] or "",
            "candidate_source": candidate["source"], "accepted_by": confirmed_by,
            "proposed_by": candidate.get("proposed_by_username")}


def save_accepted(key, record, path=None):
    path = pathlib.Path(path or ACCEPTED_PATH)
    accepted = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    accepted[key] = record
    path.write_text(json.dumps(accepted, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    if candidate["proposed_by_user_id"] == session["user_id"]:
        abort(403)
    with db.cursor() as cur:
        doc_id = create_document(cur, candidate)
        cur.execute("""UPDATE DocumentCandidate SET status = 'accepted', confirmed_by_user_id = %s,
                           confirmed_at = NOW(), document_id = %s WHERE id = %s""",
                    (session["user_id"], doc_id, candidate_id))
        audit(cur, candidate_id, "CONFIRM", {"status": "proposed"}, {"status": "accepted", "document_id": doc_id})
        cur.execute("""INSERT INTO AuditLog (table_name, record_id, action, new_value_json, changed_by_user_id)
                       VALUES ('Document', %s, 'INSERT', %s, %s)""",
                    (doc_id, json.dumps({"from_candidate": candidate_id, "identifier": candidate["designation"],
                                         "title": candidate["title"]}, ensure_ascii=False), session["user_id"]))
    db.commit()
    key = candidate["candidate_key"] or f"manual:{candidate_id}"
    save_accepted(key, pipeline_record(candidate, session.get("username")))
    flash("Kandidát přijat a dokument založen.", "success")
    return redirect(url_for("admin.candidate_detail", candidate_id=candidate_id))


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
                               areas=cd.SCOPE_AREAS, form=request.form)
    with db.cursor() as cur:
        cur.execute("""INSERT INTO DocumentCandidate (candidate_key, source, evidence_json) VALUES (%s, 'manual', %s)""",
                    (key, json.dumps({"proposed_manually": True}, ensure_ascii=False)))
        candidate_id = cur.lastrowid
        _store_proposal(cur, candidate_id, metadata)
        audit(cur, candidate_id, "PROPOSE", {}, {"status": "proposed", "manual": True, **metadata})
    db.commit()
    flash("Návrh dokumentu uložen — čeká na potvrzení jiným editorem.", "success")
    return redirect(url_for("admin.candidate_list"))
