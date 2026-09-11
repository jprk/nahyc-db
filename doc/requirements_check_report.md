# Requirements compliance report

**Generated:** 2026-09-11 16:15 · **Commit:** `ebc1f60` + R1.2/R1.3/R1.4/R1.5/R1.7/R4.1 fixes (this commit)
**Against:** `doc/REQUIREMENTS.md` (dated 2026-09-11 15:37)

Produced by `.claude/agents/requirements-check.md` (mechanical evidence
from `src/tools/check_requirements.py`, cross-referenced against
`app/app.py`, `app/templates/*.html`, `doc/konsolidace/*.sql`, `wsgi.py`).
This file is **overwritten** on every run — it is a current snapshot, not
an accumulating log.

## R1.x Data Architecture & Management

| Req | Verdict | Evidence | Gap |
|---|---|---|---|
| R1.1 Record uniqueness | PARTIAL | `Document.identifier` has a real `UNIQUE` constraint (`uq_document_identifier`). 1165/1211 documents have a non-NULL identifier. | The other 46 have `identifier IS NULL` — MariaDB allows unlimited NULLs under a UNIQUE constraint, so these bypass the physical uniqueness guarantee entirely (mostly known, disclosed residuals — cross-jurisdiction identifier collisions and one designation too long for the column — but the *mechanism* doesn't "physically prevent" every case as worded). |
| R1.2 Jurisdictional tiering (int'l / EU / national) | PASS *(fixed 2026-09-11)* | New `Document.jurisdikce_uroven ENUM('mezinárodní','EU','národní')`, a `GENERATED ALWAYS AS (...) VIRTUAL` column derived from `jurisdikce` — always in sync, no separate maintenance logic. Distribution: `národní` 773 (`SK`/`DE`/`US`/`CZ`/`CA`/`FR`/`UK` — any real country code, incl. future ones like `PL`, with no code change needed), `mezinárodní` 198, `EU` 56, `NULL` 184 (the pre-existing `neurčeno`/unknown residual — left honestly unclassified, not force-guessed into one of the three tiers). | `jurisdikce` itself is unchanged and still the veto used to keep national adoptions of the same standard from merging — `jurisdikce_uroven` is the new, additional 3-tier categorization R1.2 asks for. |
| R1.3 EU→national transposition links | PARTIAL *(mechanism built 2026-09-11)* | New `src/tools/link_document_relations_auto.py` mechanically extracts EU-act references from every non-EU-styled record's `nazev_eu`/`odkaz_eu` and links to the cited act when it already exists as its own `Document`. Actual rows: `AMENDS` ×1, `ADOPTS` ×17, `IMPLEMENTS` ×0. | The mechanism now exists and correctly excludes EU-to-EU false positives (an EU delegated act citing its own parent directive), but 0 real `IMPLEMENTS` edges exist yet because the cited EU acts (e.g. `2019/692`, `2018/858`, `2013/732`) aren't in the corpus as their own records — a data-completeness gap, not a mechanism gap. 6 candidates await a decision in `data/eu_transposition_missing_targets.json`. |
| R1.4 Standard localization linking (ISO ↔ ČSN EN ISO) | PASS *(fixed 2026-09-11)* | Same mechanism groups records by international designation core and jurisdikce tier; every national/EU "child" gets an `ADOPTS` edge to every international/EU "parent" in its group. 17 real edges loaded (e.g. `STN EN ISO 11114-4/... ADOPTS ISO 11114-4`, `ČSN ISO 14687 ADOPTS ISO 14687`). | The jurisdikce veto still correctly prevents merging them; they are now also explicitly *linked*, for the subset of adoptions whose international parent is itself present as a record in the corpus (most STN/ČSN/DIN adoptions still lack a collected international-parent record at all — a data-completeness gap, not a linking-mechanism gap). |
| R1.5 Lifecycle & version control (active/superseded/draft) | PASS *(fixed 2026-09-11)* | New `DocumentVersion.lifecycle_state ENUM('active','superseded','draft') NOT NULL DEFAULT 'active'`, computed in Python at import time (`classify_lifecycle_state()`, `src/tools/init_db.py`) from `is_current` plus real draft/work-item markers found in `platnost`/`effective_date` (`"Entwurf"`/`"Návrh"`, `"Arbeitsdokument"`/`"pracovný dokument"`, `"PWI"`). Real distribution: `active` 1035, `draft` 153, `superseded` 20 (of 1208 `DocumentVersion` rows). | None — the three states R1.5 names are now explicit and populated from genuine evidence in the corpus, not guessed. |
| R1.6 Authoritative source identification | PASS | `DocumentSource` is a separate table (40 rows), joined via `Document.source_id`, filterable independently. | — |
| R1.7 General metadata incl. file paths | PASS *(fixed 2026-09-11)* | `Document.file_path` now populated by `src/tools/init_db.py`'s `resolve_file_path()` from `data/fulltext_manifest.json` (69/1188 documents, real locally-cached full text). `app/app.py` now selects it and serves it via `/fulltext/<id>`. | None — a document without a locally-cached copy simply has `file_path IS NULL`, which is correct, not a gap. |
| R1.8 Thematic indexing (M:N keywords) | PASS | `Keyword` (228 rows) / `DocumentKeyword` (3231 rows) many-to-many join, no duplication. | — |
| R1.9 Automated/semi-automated maintenance | PASS | Full pipeline present and used all session: `build_unified_db.py` → `deduplicate_db.py` → `link_document_versions.py` → `init_db.py` → `load_document_relations.py` → `load_process_layer.py`, all in `src/tools/`. | — |

## R2.x Search & Functional Capabilities

| Req | Verdict | Evidence | Gap |
|---|---|---|---|
| R2.1 Search result uniqueness | PASS *(fixed 2026-09-11, commit `ebc1f60`)* | `app/app.py:81`: `base_query += " GROUP BY d.id ORDER BY d.title ASC LIMIT 100"`. Verified: `CGA G-5`/`OSHA 1910.103` (both titled plain "Hydrogen") now both appear as separate results. | Was: grouped by title text, not `d.id` — collapsed the keyword-join fan-out correctly in the common case, but silently merged genuinely *different* documents sharing a title. Fixed by grouping on the primary key instead. |
| R2.2 Responsive web UI | PASS | `app/templates/base.html`: viewport meta tag present. `app/static/style.css`: two real breakpoints, `@media (max-width: 992px)` and `@media (max-width: 768px)`. | — |
| R2.3 Combined full-text + structured filters | PASS | Single GET form; `app/app.py` reads `q`, `type_id`, `source_id`, `keyword_id` from `request.args` and ANDs them all onto one query. | — |
| R2.4 Result metadata summary + hyperlink | PASS | `app/templates/index.html` renders type/title/language/keywords/source/date/description per row, with a conditional hyperlink on `doc.url` (falls back to a disabled "Zdroj nedostupný" label when empty). | — |
| R2.5 Export readiness (CSV/JSON/XML) | FAIL | No `csv`/`export`/`xml` reference anywhere in `app/app.py` or the templates. | No export route or UI element exists at all — not just "not built yet" but no scaffolding/readiness either. |

## R3.x Technical Stack

| Req | Verdict | Evidence | Gap |
|---|---|---|---|
| R3.1 Python + Flask backend | PASS | `app/app.py`: `from flask import Flask, render_template, request, g`. | — |
| R3.2 Relational DB ("currently SQLite") | **MISMATCH** | `doc/REQUIREMENTS.md` says SQLite. The live, actively-maintained app (`app/app.py`) connects to **MariaDB** (`h2regdocs` via `pymysql`, `.env`: `DB_HOST=localhost`, `DB_PORT=3306`) — and `wsgi.py` now correctly points at that app too (fixed, see "Other findings"). | Not a bug to silently "fix" either direction — the requirements doc and reality disagree. A **second**, legacy Flask app at `Web/app.py` genuinely does use `sqlite3` against `Databaze/regulatory_documents.db`, but it is explicitly a temporary/experimental leftover per `CLAUDE.md`, not the canonical app. |
| R3.3 HTML5/CSS3/Jinja2 | PASS | `<!DOCTYPE html>`, CSS3 variables/`@media`/gradients in `style.css`, Jinja2 `{% extends %}`/`{{ }}` throughout `index.html`/`base.html`, rendered via `render_template`. | — |
| R3.4 Vanilla JS + Phosphor Icons + Google Fonts | PASS | One inline vanilla-JS `<script>` block in `base.html` (accordion expand/collapse, no framework). Phosphor Icons via `<script src="https://unpkg.com/@phosphor-icons/web">` + `ph`/`ph-fill` classes throughout. Google Fonts (`Inter`, `Outfit`) via `fonts.googleapis.com`. No jQuery/Bootstrap-JS/React/Vue found anywhere under `app/`. | — |

## R4.x Access Control & Licensing

| Req | Verdict | Evidence | Gap |
|---|---|---|---|
| R4.1 Licensing/visibility rules (metadata public, full text restricted) | PASS *(fixed 2026-09-11)* | New `DocumentType.restricted_fulltext BOOLEAN` (`TRUE` only for `"Norma"`) plus a new `/fulltext/<id>` route in `app/app.py` that checks it fresh on every request — 404 with no `file_path`, 403 when restricted, path-traversal-checked `send_file()` otherwise. Verification found this gate is genuinely load-bearing, not theoretical: `fetch_fulltext.py`'s own source-based exclusion had missed 2 real `"Norma"`-typed documents that got a `file_path` anyway (harmless content in this case, but proves the point) — both correctly return 403 via the new route. | None — the enforcement is now explicit and DB-driven, independent of whether `file_path` happens to be populated. `fetch_fulltext.py` also gained a second, designation-shape-based guard (`is_norm_designation()`) so this can't recur going forward. |
| R4.2 Central public hub for stakeholders | N/A | Organizational/qualitative — not mechanically checkable. The app is publicly reachable with no login and serves all metadata to any visitor, which is *consistent* with the framing, but there's no way to verify "diverse stakeholders... state administration, industrial manufacturers, transport operators, research institutions" actually use it from code alone. | — |

## Other findings (not tied to a specific requirement)

- **`wsgi.py` pointed at the wrong, legacy app — fixed 2026-09-11, commit `ebc1f60`.** It read `from Web.app import app`. `Web/` at the repo root is a real, importable Flask app (`Web/app.py`) — but it was the **old, pre-migration implementation**: plain `sqlite3` against `Databaze/regulatory_documents.db`, lowercase table names (`documents`, `document_types`, ...) that no longer match the current MariaDB PascalCase schema (`Document`, `DocumentType`, ...) this entire session's pipeline builds. `CLAUDE.md` explicitly calls `Databaze/` and `Web/` **temporary/experimental directories, not the final placement** — the canonical app is `app/app.py`. Fixed to `from app.app import app`, verified via direct import. (Interestingly, `Web/app.py`'s own search query already correctly used `SELECT DISTINCT d.id, ...` — the R2.1 grouping bug above was introduced during the migration to `app/app.py`, not inherited from the old app.) Also noteworthy: `wsgi.py` had never actually been committed to this repo's git history before this fix.
- **Duplicate `Web.zip` archives.** `app/Web.zip` and `Web/Web.zip` were byte-identical (122774 bytes, same MD5). The user removed `Web/Web.zip` (2026-09-11); `app/Web.zip` (122774 bytes) still remains, untouched, in case only one was intended to go.

## Punch list

**Cheap, safe, low-risk (no design decision needed):**
1. ~~`app/app.py:81` — change `GROUP BY d.title` to `GROUP BY d.id` (R2.1).~~ **Done, commit `ebc1f60`.**
2. ~~Fix `wsgi.py`'s import target.~~ **Done, commit `ebc1f60`.**
3. `app/Web.zip` (122774 bytes) is still present — confirm with the project owner whether it should be removed too (its twin `Web/Web.zip` already was).

**Bigger, needs a design decision from the project owner:**
4. ~~R1.2 — design the actual 3-tier jurisdiction categorization...~~ **Done, `jurisdikce_uroven` generated column, see above.**
5. ~~R1.3/R1.4 — decide how to populate `document_relation`...~~ **Mechanism built, `src/tools/link_document_relations_auto.py`, see above.** Remaining, genuinely open: whether to add the missing EU-act `Document` rows named in `data/eu_transposition_missing_targets.json` (would let R1.3 produce real `IMPLEMENTS` edges), and whether to collect the missing international-standard parent records for the STN/ČSN/DIN adoptions that still lack one (would grow R1.4's 17 edges).
6. ~~R1.5 — decide whether to add a structured lifecycle-state column...~~ **Done, `DocumentVersion.lifecycle_state`, see above.**
7. ~~R1.7/R4.1 — decide whether `file_path` should actually be populated...~~ **Done, `file_path` populated + `DocumentType.restricted_fulltext` + `/fulltext/<id>` route, see above.**
8. R2.5 — decide which export formats/scope to actually build (or confirm "modular and extensible" is satisfied structurally without a concrete export feature yet).
9. R3.2 — resolve the SQLite-vs-MariaDB wording mismatch in `doc/REQUIREMENTS.md` itself (update the doc, or treat MariaDB as an approved deviation).
