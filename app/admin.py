"""Editor accounts, a staged two-editor review workflow for
`Document.needs_review` records, and an audit log — doc/PLAN.md §42,
2026-09-18, user-directed.

A proposed correction (`ReviewItem.proposed_changes_json`) never touches
the live `Document` row on its own — only when a SECOND, different
editor confirms it (enforced here AND by the database's own
`chk_ri_distinct_reviewers` CHECK constraint, doc/konsolidace/
Konsolidace-DB-schema.sql). Confirming writes the live `Document` row
immediately (public visibility right away) AND appends to
`data/manual_corrections.json` (`src/tools/build_unified_db.py`'s
`apply_manual_corrections()`), so the fix survives the next full
pipeline rebuild instead of being silently erased by it — the same
"never patch downstream only" discipline every other `apply_*()` overlay
in this project already follows.

Editable fields are named after the JSON PIPELINE's own field names
(`znacka`/`nazev_cz`/`anotace_poznamka`), not the live `Document` column
names (`identifier`/`title`/`description`) — `proposed_changes_json` and
`data/manual_corrections.json` both speak the pipeline's vocabulary
directly, since that's what `apply_manual_corrections()` actually reads;
`_LIVE_COLUMN_BY_FIELD` is the one place translating to the live column
each corresponds to, only used when writing the immediate `Document`
UPDATE.
"""
import functools
import json
import os
import pathlib
import sys

import pymysql
from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
from init_db import is_garbled_znacka, is_fragment_title  # noqa: E402

admin_bp = Blueprint("admin", __name__)

MANUAL_CORRECTIONS_PATH = REPO_ROOT / "data" / "manual_corrections.json"


def get_db():
    """Deliberately its own copy of `app.app.get_db()`, not an import of
    it — `app/app.py` can run either as a directly-executed script
    (`.venv/bin/python app/app.py`, dev server) or as a package import
    (`wsgi.py`'s `from app.app import app`), and those two modes put
    different directories on `sys.path`; a cross-import between the two
    sibling modules would work under one mode and silently break under
    the other. `flask.g`/`os.environ` are true global proxies regardless
    of which mode loaded this module, so duplicating these 8 lines is
    safer than fighting Python's import system over it."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = pymysql.connect(
            host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
            user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
        )
    return db

# JSON-pipeline field name -> (live Document column, form label).
EDITABLE_FIELDS = {
    "znacka": ("identifier", "Značka"),
    "nazev_cz": ("title", "Název"),
    "anotace_poznamka": ("description", "Popis/anotace"),
}

_OPEN_REVIEW_STATUSES = ("needs_review", "proposed")


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("admin/login.html")

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id, name, password_hash, is_active FROM User WHERE username=%s", (username,))
        user = cur.fetchone()
    if not user or not user["is_active"] or not check_password_hash(user["password_hash"], password):
        flash("Neplatné přihlašovací jméno nebo heslo.", "error")
        return render_template("admin/login.html")

    session["user_id"] = user["id"]
    session["username"] = username
    session["name"] = user["name"]
    return redirect(request.args.get("next") or url_for("admin.review_list"))


@admin_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


def fetch_review_list(db):
    """Every `needs_review` `Document`, each paired with its currently
    OPEN `ReviewItem` if one exists (`NULL` review_item_id/status means
    "flagged, nobody has proposed anything yet") — a single query rather
    than pre-creating a `ReviewItem` row for every flagged document up
    front (~340 of them today), which stays lazy: a row is only created
    once an editor actually proposes something (see `propose()` below)."""
    with db.cursor() as cur:
        cur.execute("""
            SELECT d.id AS document_id, d.slug, d.identifier, d.title, d.review_reason,
                   ri.id AS review_item_id, ri.status AS review_status,
                   ri.proposed_by_user_id, pu.username AS proposed_by_username,
                   pu.name AS proposed_by_name
            FROM Document d
            LEFT JOIN ReviewItem ri
                ON ri.document_id = d.id AND ri.status IN ('needs_review', 'proposed')
            LEFT JOIN User pu ON pu.id = ri.proposed_by_user_id
            WHERE d.needs_review = 1
            ORDER BY d.id
        """)
        return cur.fetchall()


@admin_bp.route("/review")
@login_required
def review_list():
    return render_template("admin/review_list.html", items=fetch_review_list(get_db()))


def fetch_document_for_review(db, document_id):
    with db.cursor() as cur:
        cur.execute("""
            SELECT id, slug, identifier, title, description, needs_review, review_reason
            FROM Document WHERE id=%s
        """, (document_id,))
        return cur.fetchone()


def fetch_open_review_item(db, document_id):
    with db.cursor() as cur:
        cur.execute("""
            SELECT * FROM ReviewItem
            WHERE document_id=%s AND status IN ('needs_review', 'proposed')
            ORDER BY id DESC LIMIT 1
        """, (document_id,))
        return cur.fetchone()


@admin_bp.route("/review/<int:document_id>/edit", methods=["GET", "POST"])
@login_required
def propose(document_id):
    db = get_db()
    document = fetch_document_for_review(db, document_id)
    if document is None:
        abort(404)

    if request.method == "GET":
        return render_template("admin/review_edit.html", document=document,
                                fields=EDITABLE_FIELDS)

    changes = {}
    for field, (live_column, _label) in EDITABLE_FIELDS.items():
        value = (request.form.get(field) or "").strip()
        if value and value != (document.get(live_column) or ""):
            changes[field] = value
    if not changes:
        flash("Žádná pole nebyla změněna.", "error")
        return render_template("admin/review_edit.html", document=document,
                                fields=EDITABLE_FIELDS)

    with db.cursor() as cur:
        existing = fetch_open_review_item(db, document_id)
        if existing:
            cur.execute("""
                UPDATE ReviewItem
                SET status='proposed', proposed_changes_json=%s,
                    proposed_by_user_id=%s, proposed_at=NOW()
                WHERE id=%s
            """, (json.dumps(changes, ensure_ascii=False), session["user_id"], existing["id"]))
        else:
            cur.execute("""
                INSERT INTO ReviewItem
                    (document_id, review_reason, status, proposed_changes_json,
                     proposed_by_user_id, proposed_at)
                VALUES (%s, %s, 'proposed', %s, %s, NOW())
            """, (document_id, document["review_reason"],
                  json.dumps(changes, ensure_ascii=False), session["user_id"]))
    db.commit()
    flash("Návrh opravy uložen — čeká na potvrzení jiným editorem.", "success")
    return redirect(url_for("admin.review_list"))


def fetch_review_item(db, review_item_id):
    with db.cursor() as cur:
        cur.execute("""
            SELECT ri.*, d.slug, d.identifier, d.title, d.description,
                   pu.username AS proposed_by_username, pu.name AS proposed_by_name
            FROM ReviewItem ri
            JOIN Document d ON d.id = ri.document_id
            LEFT JOIN User pu ON pu.id = ri.proposed_by_user_id
            WHERE ri.id=%s
        """, (review_item_id,))
        return cur.fetchone()


def load_manual_corrections():
    if MANUAL_CORRECTIONS_PATH.exists():
        with open(MANUAL_CORRECTIONS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manual_corrections(corrections):
    with open(MANUAL_CORRECTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(corrections, f, ensure_ascii=False, indent=2, sort_keys=True)


def recompute_needs_review(identifier, title, description):
    """Re-derives `needs_review`/`review_reason` from the POST-correction
    values, using the exact same checks `init_db.py`'s own `detect_data_
    quality_issues()` runs at import time (`is_garbled_znacka`,
    `is_fragment_title`, an empty description) — reused directly, not
    reimplemented, so a confirmed fix is judged by the identical rule
    that flagged it in the first place."""
    reasons = []
    if is_garbled_znacka(identifier):
        reasons.append("značka není platné označení dokumentu")
    if is_fragment_title(title):
        reasons.append("název vypadá jako useknutý fragment textu")
    if not (description or "").strip():
        reasons.append("chybí popis/anotace dokumentu")
    return bool(reasons), ("; ".join(reasons) or None)


@admin_bp.route("/review/<int:review_item_id>/confirm", methods=["GET", "POST"])
@login_required
def confirm(review_item_id):
    db = get_db()
    item = fetch_review_item(db, review_item_id)
    if item is None:
        abort(404)
    if item["status"] != "proposed":
        flash("Tato položka už není otevřená k rozhodnutí.", "error")
        return redirect(url_for("admin.review_list"))
    if item["proposed_by_user_id"] == session["user_id"]:
        abort(403)

    proposed_changes = json.loads(item["proposed_changes_json"] or "{}")

    if request.method == "GET":
        return render_template("admin/review_confirm.html", item=item,
                                proposed_changes=proposed_changes, fields=EDITABLE_FIELDS)

    action = request.form.get("action")
    with db.cursor() as cur:
        if action == "reject":
            cur.execute("""
                UPDATE ReviewItem
                SET status='rejected', confirmed_by_user_id=%s, confirmed_at=NOW(),
                    rejection_note=%s
                WHERE id=%s
            """, (session["user_id"], (request.form.get("rejection_note") or "").strip(), review_item_id))
            db.commit()
            flash("Návrh zamítnut.", "success")
            return redirect(url_for("admin.review_list"))

        if action != "confirm":
            abort(400)

        old_row = fetch_document_for_review(db, item["document_id"])
        new_identifier = proposed_changes.get("znacka", old_row["identifier"])
        new_title = proposed_changes.get("nazev_cz", old_row["title"])
        new_description = proposed_changes.get("anotace_poznamka", old_row["description"])
        needs_review, review_reason = recompute_needs_review(new_identifier, new_title, new_description)

        cur.execute("""
            UPDATE Document
            SET identifier=%s, title=%s, description=%s, needs_review=%s, review_reason=%s
            WHERE id=%s
        """, (new_identifier, new_title, new_description, needs_review, review_reason,
              item["document_id"]))

        cur.execute("""
            INSERT INTO AuditLog (table_name, record_id, action, old_value_json,
                                   new_value_json, changed_by_user_id, review_item_id)
            VALUES ('Document', %s, 'UPDATE', %s, %s, %s, %s)
        """, (item["document_id"],
              json.dumps(old_row, ensure_ascii=False, default=str),
              json.dumps({**old_row, "identifier": new_identifier, "title": new_title,
                          "description": new_description, "needs_review": needs_review,
                          "review_reason": review_reason}, ensure_ascii=False, default=str),
              session["user_id"], review_item_id))

        cur.execute("""
            UPDATE ReviewItem
            SET status='confirmed', confirmed_by_user_id=%s, confirmed_at=NOW()
            WHERE id=%s
        """, (session["user_id"], review_item_id))
    db.commit()

    # doc/PLAN.md §42: survive the next pipeline rebuild, not just the
    # live database — see build_unified_db.apply_manual_corrections().
    key = old_row["identifier"]
    if key:
        corrections = load_manual_corrections()
        corrections[key] = {
            "changes": proposed_changes,
            "confirmed_by": session["username"],
            "confirmed_at": str(item.get("confirmed_at") or ""),
        }
        save_manual_corrections(corrections)

    flash("Oprava potvrzena a zapsána.", "success")
    return redirect(url_for("admin.review_list"))


@admin_bp.route("/audit-log")
@login_required
def audit_log():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            SELECT a.*, u.username AS changed_by_username, u.name AS changed_by_name, d.slug, d.title
            FROM AuditLog a
            LEFT JOIN User u ON u.id = a.changed_by_user_id
            LEFT JOIN Document d ON d.id = a.record_id AND a.table_name = 'Document'
            ORDER BY a.id DESC
            LIMIT 200
        """)
        entries = cur.fetchall()
    return render_template("admin/audit_log.html", entries=entries)
