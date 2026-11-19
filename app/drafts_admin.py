"""Editor pages for prepared documents (doc/MPO_PRIPOMINKY.md, krok 3): a draft
(`DocumentVersion.lifecycle_state = 'draft'`, připravovaný) that has been
promulgated is marked as promulgated or in effect and joined to the act
(src/tools/state_changes.py describes the two ways).

* **Two editors**, as for a correction (admin.py) or the acceptance of a candidate
  (candidates_admin.py): one proposes the change, a second, different editor
  confirms it (also enforced by the CHECK constraint `chk_dsc_distinct_reviewers`);
  the proposer may withdraw a proposal that has not been confirmed.
* **The confirmation** writes the live database at once (the state of the current
  version, the changed fields, the `ENACTED_AS` relation, the date of the last check
  of the state with the confirming editor as its source) and the files a rebuild
  reads (data/manual_corrections.json, data/document_relations_editor.json).

Every step is written to the AuditLog (`table_name` = `DocumentStateChange`; the
change of a document also as `Document` / `UPDATE`).
"""
import datetime
import json

import pymysql
from flask import abort, flash, redirect, render_template, request, session, url_for

from admin import admin_bp, get_db, login_required, recompute_needs_review
import state_changes as sc
import status_checks

LIFECYCLE_LABELS = {"active": "účinný", "superseded": "nahrazený", "draft": "připravovaný",
                    "promulgated": "vyhlášený, dosud neúčinný", "repealed": "zrušený"}
MISSING_SCHEMA = (1146, 1054)  # unknown table / column: the migration has not been run on this database


def audit(cur, table, record_id, action, old, new):
    cur.execute("""INSERT INTO AuditLog (table_name, record_id, action, old_value_json, new_value_json,
                                         changed_by_user_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (table, record_id, action, json.dumps(old, ensure_ascii=False, default=str),
                 json.dumps(new, ensure_ascii=False, default=str), session["user_id"]))


def fetch_document(db, document_id):
    """The document with its current version, or None."""
    with db.cursor() as cur:
        cur.execute("""SELECT d.id, d.slug, d.identifier, d.title, d.url, d.effective_date, d.description,
                              d.language, d.jurisdikce, dt.name AS type_name,
                              dv.id AS version_id, dv.lifecycle_state
                       FROM Document d
                       LEFT JOIN DocumentType dt ON dt.id = d.type_id
                       LEFT JOIN DocumentVersion dv ON dv.document_id = d.id AND dv.is_current = 1
                       WHERE d.id = %s""", (document_id,))
        return cur.fetchone()


def fetch_changes(db, document_id=None, status=None):
    conditions, params = [], []
    if document_id is not None:
        conditions.append("(c.document_id = %s OR c.target_document_id = %s)")
        params += [document_id, document_id]
    if status:
        conditions.append("c.status = %s")
        params.append(status)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    with db.cursor() as cur:
        cur.execute(f"""SELECT c.*, d.slug, d.identifier, d.title, t.slug AS target_slug,
                               t.identifier AS target_identifier, t.title AS target_title,
                               pu.name AS proposed_by_name, cu.name AS confirmed_by_name
                        FROM DocumentStateChange c
                        JOIN Document d ON d.id = c.document_id
                        LEFT JOIN Document t ON t.id = c.target_document_id
                        LEFT JOIN User pu ON pu.id = c.proposed_by_user_id
                        LEFT JOIN User cu ON cu.id = c.confirmed_by_user_id
                        {where} ORDER BY c.id DESC LIMIT 200""", params)
        rows = cur.fetchall()
    for row in rows:
        row["changes"] = json.loads(row["changes_json"] or "{}")
    return rows


def schema_missing(error):
    return isinstance(error, (pymysql.err.ProgrammingError, pymysql.err.OperationalError)) \
        and error.args and error.args[0] in MISSING_SCHEMA


def migration_page():
    flash("V databázi chybí tabulka DocumentStateChange — spusťte migraci "
          "(src/tools/backfill_document_states.py --apply).", "error")
    return redirect(url_for("admin.review_list"))


@admin_bp.route("/drafts")
@login_required
def draft_list():
    db = get_db()
    query = (request.args.get("q") or "").strip()
    conditions, params = ["dv.lifecycle_state = 'draft'"], []
    if query:
        conditions.append("(d.title LIKE %s OR d.identifier LIKE %s)")
        params += [f"%{query}%", f"%{query}%"]
    try:
        proposed = fetch_changes(db, status="proposed")
        confirmed = fetch_changes(db, status="confirmed")[:20]
    except pymysql.err.MySQLError as error:
        if schema_missing(error):
            return migration_page()
        raise
    with db.cursor() as cur:
        cur.execute(f"""SELECT d.id, d.slug, d.identifier, d.title, dt.name AS type_name, d.effective_date
                        FROM Document d
                        JOIN DocumentVersion dv ON dv.document_id = d.id AND dv.is_current = 1
                        LEFT JOIN DocumentType dt ON dt.id = d.type_id
                        WHERE {' AND '.join(conditions)}
                        ORDER BY dt.name, d.identifier, d.title LIMIT 500""", params)
        drafts = cur.fetchall()
    pending = {row["document_id"] for row in proposed}
    return render_template("admin/drafts_list.html", drafts=drafts, proposed=proposed, confirmed=confirmed,
                           pending=pending, query=query, modes=sc.MODES, target_states=sc.TARGET_STATES)


@admin_bp.route("/drafts/<int:document_id>")
@login_required
def draft_detail(document_id):
    db = get_db()
    document = fetch_document(db, document_id)
    if document is None:
        abort(404)
    try:
        history = fetch_changes(db, document_id=document_id)
    except pymysql.err.MySQLError as error:
        if schema_missing(error):
            return migration_page()
        raise
    open_change = next((c for c in history if c["status"] == "proposed" and c["document_id"] == document_id), None)
    return render_template("admin/draft_detail.html", d=document, history=history, open_change=open_change,
                           modes=sc.MODES, target_states=sc.TARGET_STATES, status_labels=sc.STATUS_LABELS,
                           lifecycle=LIFECYCLE_LABELS, fields=sc.FIELDS)


def find_target(db, designation, document_id):
    """(target document or None, error message or None)."""
    with db.cursor() as cur:
        cur.execute("""SELECT d.id, d.identifier, d.title, dv.lifecycle_state FROM Document d
                       LEFT JOIN DocumentVersion dv ON dv.document_id = d.id AND dv.is_current = 1
                       WHERE d.identifier = %s""", (designation,))
        target = cur.fetchone()
    if target is None:
        return None, f"Dokument s označením {designation} v databázi není — zvolte „{sc.MODES['self']}“."
    if target["id"] == document_id:
        return None, "Vyhlášený předpis musí být jiný dokument než návrh."
    return target, None


@admin_bp.route("/drafts/<int:document_id>/propose", methods=["POST"])
@login_required
def draft_propose(document_id):
    db = get_db()
    document = fetch_document(db, document_id)
    if document is None:
        abort(404)
    back = redirect(url_for("admin.draft_detail", document_id=document_id))
    if document["lifecycle_state"] != "draft":
        flash("Dokument už není připravovaný.", "error")
        return back
    if any(c["status"] == "proposed" and c["document_id"] == document_id for c in fetch_changes(db, document_id)):
        flash("Ke dokumentu už jeden návrh čeká na potvrzení.", "error")
        return back
    proposal, errors = sc.read_proposal(request.form)
    target = None
    if proposal["mode"] == "act" and proposal["target"]:
        target, error = find_target(db, proposal["target"], document_id)
        if error:
            errors.append(error)
    changes = sc.changed_fields(document, proposal["changes"])
    new_identifier = changes.get("znacka")
    if new_identifier:
        with db.cursor() as cur:
            cur.execute("SELECT id FROM Document WHERE identifier = %s AND id <> %s", (new_identifier, document_id))
            if cur.fetchone():
                errors.append(f"Dokument s označením {new_identifier} už v databázi je — zvolte „{sc.MODES['act']}“.")
    if errors:
        for error in errors:
            flash(error, "error")
        return back
    with db.cursor() as cur:
        cur.execute("""INSERT INTO DocumentStateChange (document_id, mode, from_state, to_state, target_document_id,
                                                        changes_json, note, proposed_by_user_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (document_id, proposal["mode"], document["lifecycle_state"], proposal["to_state"],
                     target["id"] if target else None, json.dumps(changes, ensure_ascii=False) if changes else None,
                     proposal["note"] or None, session["user_id"]))
        change_id = cur.lastrowid
        audit(cur, "DocumentStateChange", change_id, "PROPOSE", {"lifecycle_state": document["lifecycle_state"]},
              {"document_id": document_id, "mode": proposal["mode"], "to_state": proposal["to_state"],
               "target_document_id": target["id"] if target else None, "changes": changes, "note": proposal["note"]})
    db.commit()
    flash("Změna stavu navržena — čeká na potvrzení jiným editorem.", "success")
    return back


def fetch_change(db, change_id):
    with db.cursor() as cur:
        cur.execute("SELECT * FROM DocumentStateChange WHERE id = %s", (change_id,))
        change = cur.fetchone()
    if change is None:
        abort(404)
    return change


@admin_bp.route("/drafts/change/<int:change_id>/withdraw", methods=["POST"])
@login_required
def draft_withdraw(change_id):
    db = get_db()
    change = fetch_change(db, change_id)
    if change["status"] != "proposed":
        flash("Návrh už není otevřený.", "error")
    elif change["proposed_by_user_id"] != session["user_id"]:
        abort(403)
    else:
        with db.cursor() as cur:
            cur.execute("UPDATE DocumentStateChange SET status = 'withdrawn' WHERE id = %s", (change_id,))
            audit(cur, "DocumentStateChange", change_id, "WITHDRAW", {"status": "proposed"}, {"status": "withdrawn"})
        db.commit()
        flash("Návrh stažen.", "success")
    return redirect(url_for("admin.draft_detail", document_id=change["document_id"]))


def set_state(cur, version_id, state):
    # the date of effect stays on Document (`platnost`), as a rebuild puts it (init_db.resolve_document_versions)
    cur.execute("UPDATE DocumentVersion SET lifecycle_state = %s WHERE id = %s", (state, version_id))


def mark_checked(cur, document_id, today, checked_by):
    cur.execute("UPDATE Document SET status_checked_at = %s, status_checked_by = %s WHERE id = %s",
                (today, checked_by, document_id))


@admin_bp.route("/drafts/change/<int:change_id>/confirm", methods=["POST"])
@login_required
def draft_confirm(change_id):
    db = get_db()
    change = fetch_change(db, change_id)
    back = redirect(url_for("admin.draft_detail", document_id=change["document_id"]))
    if change["status"] != "proposed":
        flash("Návrh už není otevřený.", "error")
        return back
    if change["proposed_by_user_id"] == session["user_id"]:
        abort(403)
    document = fetch_document(db, change["document_id"])
    if document["lifecycle_state"] != "draft":
        flash("Dokument už není připravovaný — návrh nelze potvrdit.", "error")
        return back
    changes = json.loads(change["changes_json"] or "{}")
    target = fetch_document(db, change["target_document_id"]) if change["mode"] == "act" else None
    if change["mode"] == "act" and target is None:
        flash("Vyhlášený předpis z návrhu už v databázi není.", "error")
        return back
    today = datetime.date.today().isoformat()
    checked_by = status_checks.editor_label(session.get("name"))
    corrections = sc.load_json(sc.MANUAL_CORRECTIONS_PATH, {})
    persist, relation = [], None
    with db.cursor() as cur:
        if change["mode"] == "self":
            if changes.get("znacka"):
                cur.execute("SELECT id FROM Document WHERE identifier = %s AND id <> %s",
                            (changes["znacka"], document["id"]))
                if cur.fetchone():
                    flash(f"Dokument s označením {changes['znacka']} už v databázi je.", "error")
                    return back
            new = {column: changes.get(field, document[column]) for field, column in sc.FIELDS.items()}
            needs_review, review_reason = recompute_needs_review(new["identifier"], new["title"],
                                                                 document["description"])
            cur.execute("""UPDATE Document SET identifier = %s, title = %s, url = %s, effective_date = %s,
                                  needs_review = %s, review_reason = %s WHERE id = %s""",
                        (new["identifier"], new["title"], new["url"], new["effective_date"], needs_review,
                         review_reason, document["id"]))
            set_state(cur, document["version_id"], change["to_state"])
            mark_checked(cur, document["id"], today, checked_by)
            audit(cur, "Document", document["id"], "UPDATE",
                  {**{c: document[c] for c in sc.FIELDS.values()}, "lifecycle_state": document["lifecycle_state"]},
                  {**new, "lifecycle_state": change["to_state"], "state_change_id": change_id})
            persist.append((sc.correction_key(document["identifier"], document["url"], corrections),
                            {**changes, "stav_dokumentu": change["to_state"], "stav_overen": today,
                             "stav_overil": checked_by}))
        else:
            set_state(cur, document["version_id"], "superseded")
            mark_checked(cur, document["id"], today, checked_by)
            cur.execute("""INSERT IGNORE INTO document_relation (from_document_id, to_document_id, relation_type, note)
                           VALUES (%s, %s, %s, %s)""",
                        (document["id"], target["id"], sc.RELATION, "Návrh vyhlášen jako tento předpis (editor)."))
            target_state = target["lifecycle_state"]
            if target_state != "repealed":
                target_state = change["to_state"]
                set_state(cur, target["version_id"], target_state)
                mark_checked(cur, target["id"], today, checked_by)
            audit(cur, "Document", document["id"], "UPDATE", {"lifecycle_state": "draft"},
                  {"lifecycle_state": "superseded", "enacted_as": target["id"], "state_change_id": change_id})
            audit(cur, "Document", target["id"], "UPDATE", {"lifecycle_state": target["lifecycle_state"]},
                  {"lifecycle_state": target_state, "enacts_draft": document["id"], "state_change_id": change_id})
            persist.append((sc.correction_key(document["identifier"], document["url"], corrections),
                            {"stav_dokumentu": "superseded", "stav_overen": today, "stav_overil": checked_by}))
            persist.append((sc.correction_key(target["identifier"], target["url"], corrections),
                            {"stav_dokumentu": target_state, "stav_overen": today, "stav_overil": checked_by}))
            if document["identifier"] and target["identifier"]:
                relation = (document["identifier"], target["identifier"])
        cur.execute("""UPDATE DocumentStateChange SET status = 'confirmed', confirmed_by_user_id = %s,
                           confirmed_at = NOW() WHERE id = %s""", (session["user_id"], change_id))
        audit(cur, "DocumentStateChange", change_id, "CONFIRM", {"status": "proposed"}, {"status": "confirmed"})
    db.commit()
    sc.save_corrections(persist, session.get("username"), today)
    if any(key is None for key, _changes in persist):
        flash("Dokument nemá označení ani adresu: změna je v databázi, přestavbu databáze ale nepřežije.", "error")
    if relation:
        sc.save_relation(*relation, "Návrh vyhlášen jako tento předpis (editor).")
    elif change["mode"] == "act":
        flash("Návrh nemá označení: vazba na vyhlášený předpis je v databázi, přestavbu databáze ale nepřežije.",
              "error")
    flash("Změna stavu potvrzena a zapsána.", "success")
    return back
