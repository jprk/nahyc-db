# Database Consolidation & Automation Plan

**Project:** NAHYC DP004 — Vodíkový technologický inkubátor
**Date:** 2026-09-07
**Status:** Steps 0 and 1 executed 2026-09-07, extended through 2026-09-09
(4th source `Sinay_Normy` — Slovak/German norms — wired in with a
jurisdiction-aware dedup guard; MariaDB `h2regdocs` now holds 1344 records
from 2230 raw). Steps 2–3 and the agentic architecture in §3 are still
proposals.
**Source:** §3 below reconciles this plan against
`doc/automation_proposal/Automating Hydrogen Legislation Database
Consolidation.md` (a Gemini research-agent transcript) — see reconciliation
note at the top of §3.

## 1. Current state — two disconnected pipelines

Recon of `src/tools/`, `doc/konsolidace/`, `data/`, and the deployed `app/`
found that this repository currently holds **two pipelines that were never
connected**, and neither produces a working database today.

### Pipeline A — merge/dedup chain (`src/tools/`)

- `build_unified_db.py` concatenates the three raw sources (Prokop, Sinay,
  Haltuf) into `data/database_merged_raw.json` (281 records; Czech field
  names: `zdroj_dat`, `nazev_cz/sk/eu`, `znacka`, `typ_dokumentu`,
  `klicova_slova`, `gestor`, …). No deduplication at this stage.
- `deduplicate_db.py` clusters records by title-embedding cosine similarity
  (threshold 0.85) and asks GPT-4o-mini to merge each cluster, producing
  `data/database_merged_deduplicated.json` (165 records).
- `analyze_similarities.py` is a diagnostic that dumps 0.75–0.85 "gray zone"
  pairs for human review — its output path (`documents/similarity_analysis.md`)
  no longer exists post-reorg, so it currently fails silently on purpose.
- `enrich_eu_laws.py`, `process_laws.py`, `enrich_annotations.py` use GPT-4o
  to fill in legal mappings and annotations, with **no verification step**
  (no check that the model's claims actually appear in a source document).
- `src/tools/0README.md` is stale: it omits `deduplicate_db.py` and
  `analyze_similarities.py` entirely, and misdescribes `init_db.py`'s target.

### Pipeline B — target schema (`doc/konsolidace/`)

- `Konsolidace-DB-popis.md` + `Konsolidace-DB-schema.sql` define a complete,
  well-designed 4-layer MariaDB schema: **A** regulatory (`Document` and
  friends, extended from V01), **B** process nodes U1–U7 (from V02), **C**
  integration (`node_document`), **D** classification/compliance pathway
  (from V03).
- This schema assumes `Document` rows already exist so process nodes can be
  linked to them. **Nothing currently populates it** — layer A has no loader
  from Pipeline A's output, and layers B–D have no content at all yet.

### Where they fail to meet

- `init_db.py` / `check_db.py` hardcode `../../zip/V01/db/regulatory_documents.db`
  — wrong case (`zip/v01` is lowercase on disk) and pointing at the archival
  zip snapshot, not a canonical location. Neither script has been run
  successfully since the repo reorg.
- **No `.db` file exists anywhere in the tracked tree.**
- `app/app.py`'s `DB_PATH` resolves to `../../db/regulatory_documents.db` —
  one level *above* the repo root, outside the repository entirely. The app
  is not currently runnable against any real database.
- The existing dedup run (281→165) is **not trustworthy as-is**: the log
  shows several clusters hit `Connection error` calling the LLM, and the
  exception handler silently returned those clusters **unmerged** — an
  unknown number of the 165 "deduplicated" records may still contain
  undetected duplicates.
- Matching used title-embedding similarity only. The one deterministic key
  available — `znacka` (the legal reference/identifier number) — was never
  used, even though it is the obviously reliable dedup signal for legal
  documents (two records with the same "č. 165/2012 Sb." are the same law,
  regardless of title phrasing).
- The V01 `.docx` describes a "semi-automated + automated, weekly-verified"
  update process against EUR-Lex/e-Sbírka/ČAS. This is planning language —
  nothing in `src/tools/` currently implements scheduled source screening.

## 2. Proposed consolidation plan

### Step 0 — Provision MariaDB (prerequisite, no design changes) — DONE 2026-09-07

- **Deviation from the plan as written below:** `Konsolidace-DB-schema.sql`
  turned out NOT to be a usable standalone baseline — it opens with
  `ALTER TABLE Document/DocumentSource/DocumentVersion`, assuming the V01
  PascalCase base tables already exist (true only against the live
  production DB per `Konsolidace-DB-popis.md`). No MariaDB DDL for those
  base tables existed anywhere in the tracked tree. Reconstructed them in
  a new `doc/konsolidace/V01-baseline-schema.sql`, sourced from the
  since-deleted `db/RegulatoryDocumentsDB.puml` (recovered via `git show`
  on its last commit) plus column sizing validated against the actual
  165-record `data/database_merged_deduplicated.json` (`title` and
  `effective_date` widened past the original 255/50-char SQLite sizes —
  real EU regulation titles run past 460 chars, `gestor`/effective-date
  free text past 500).
- New `src/tools/provision_db.py` creates `h2regdocs` and applies
  `V01-baseline-schema.sql` then `Konsolidace-DB-schema.sql`, via the
  `mariadb` CLI (not a hand-rolled `;`-splitter — the schema file has a
  semicolon inside an inline SQL comment on `node_branch` that breaks naive
  splitting).
- `init_db.py` / `check_db.py` / `app/app.py` now connect to MariaDB via
  `pymysql` using `.env` (`python-dotenv`), targeting the PascalCase V01
  tables (`Document`, `DocumentType`, `DocumentSource`, `Keyword`,
  `DocumentKeyword`) instead of the old lowercase SQLite ones. Verified:
  `provision_db.py` → `init_db.py` (165 documents, 42 sources, 47 keywords
  imported) → `check_db.py` → `app/app.py` smoke-tested via Flask test
  client (search, type/source/keyword filters all return 200).
- `pymysql` and `python-dotenv` added to `.venv` — no `requirements.txt`
  exists in the repo yet to record this in; flagging here rather than
  creating one unasked.
- Not touched: `wsgi.py` (still imports `Web.app` — out of scope, see
  `CLAUDE.md` on the `app/` vs `Web/` ambiguity).

Original plan (executed as amended above):

- **Engine decision:** MariaDB from the start, not a local SQLite dev DB.
  MariaDB 11.8.6 (client) is already installed on this machine and matches
  the production target, and `Konsolidace-DB-schema.sql` is already written
  natively for MariaDB (ENUMs etc.) — going straight to it skips an entire
  SQLite↔MariaDB dialect-conversion/migration step.
- **Database name:** `h2regdocs`.
- **Credentials:** a `.env` file at the repo root (already listed in
  `.gitignore`, never committed) holding `DB_HOST`, `DB_PORT`, `DB_NAME`,
  `DB_USER`, `DB_PASSWORD`. Read the same lightweight way `.openapi_key` is
  read today (or via `python-dotenv` if preferred) — no new secret-storage
  mechanism needed.
- Since `Konsolidace-DB-schema.sql` already *is* the MariaDB baseline (it
  includes the V01-derived layer-A tables plus layers B–D), apply it
  directly as the initial schema. **This removes the old two-stage plan**
  (legacy SQLite schema first, Konsolidace DDL second) — what was
  previously "Step 3: apply the Konsolidace schema" now happens here.
- Fix `init_db.py` / `check_db.py` to connect via a MariaDB Python connector
  (e.g. `mariadb` or `PyMySQL`) using the `.env` credentials, instead of
  hardcoding a SQLite path.
- Fix `app/app.py`'s DB connection logic to the same MariaDB connection.
- Correct `src/tools/0README.md` (add missing scripts, fix `init_db.py`
  description).
- Nothing further below is meaningful until this step is done — there is
  currently no database for any of it to act on.

### Step 1 — Harden and re-run deduplication — DONE 2026-09-07

- **Also fixed while implementing this step:** `deduplicate_db.py` and
  `analyze_similarities.py` had their own latent path bug (one `.parent`
  too few — resolved to `src/`, not the repo root, so `.openapi_key` and
  `data/` were never found there either). Same root cause as Step 0's
  SQLite-path bug, different scripts, from the `Data/`→`data/` reorg.
  Discovered and fixed alongside 6 *other* `src/tools/` scripts with the
  identical `Data/` (capital, cwd-relative) bug: `build_unified_db.py`,
  `process_laws.py`, `enrich_eu_laws.py`, `parse_norms.py`,
  `process_haltuf.py`, `analyze_headers.py`, `search_agent.py`. All now use
  the `__file__`-relative `BASE_DIR`/`REPO_ROOT` pattern already used
  elsewhere (Step 0's `init_db.py` etc.).
- `enrich_annotations.py` was found to be **orphaned**: its target file
  `data/databaze_komplet.json` no longer exists and has no producer in the
  current pipeline (superseded by `database_merged_raw.json`/
  `database_merged_deduplicated.json`, a different, later architecture).
  Repointed it at `data/database_merged_deduplicated.json` instead of
  leaving it as dead code.
- `openai`, `pandas`, `openpyxl`, `duckduckgo_search` installed into
  `.venv` — none were actually present despite 5+ scripts importing them.
- **Deterministic `znacka` pre-pass:** implemented via a Union-Find over
  `deduplicate_db.py`'s candidate records — records sharing a normalized
  `znacka` are unioned into the same cluster regardless of what cosine
  similarity says, merged with the existing embedding-based clustering in
  one pass. Each final cluster is labeled `match_type: "deterministic"` or
  `"semantic"` in the audit log below.
- **Retry + escalate:** `deduplicate_cluster_with_llm()` now retries up to
  3 times (short backoff) on an LLM call error. On exhausting retries, the
  cluster's records are no longer silently returned unmerged (the original
  bug) — they're tagged `_dedup_status: "flagged_for_review"`, kept in the
  output (never dropped), and appended to a new
  `data/dedup_review_queue.json`.
- **Structural sanity check:** a successful-looking merge is rejected
  (treated like a failed attempt, triggering the same retry/escalate path)
  if it invents a `znacka` not present in any input record — see §3.5 for
  why this is the right-sized check here, rather than the proposal's
  verbatim-quote verification.
- **Audit log:** `data/dedup_audit_log.jsonl`, one line per cluster —
  `cluster_id`, member titles/`znacka`, `match_type`, `action` (`merged` /
  `kept_separate` / `flagged_for_review`), timestamp.
- **Gray-zone gate:** `analyze_similarities.py`'s output path fixed to
  `doc/similarity_analysis.md` (`documents/` no longer exists post-reorg).
  `deduplicate_db.py` now prints a reminder pointing at it (and at the
  review queue, if non-empty) when it finishes, instead of implying its
  output is final.
- **Re-run results:** `deduplicate_db.py` produced **159 records** from the
  281-record raw file — 98 clusters had no duplicate (`kept_separate`), 49
  were merged, of which **8 clusters were caught by the deterministic
  `znacka` match**. **0 clusters were flagged for review** (no LLM
  failures) and all 159 output records kept a non-empty `anotace_poznamka`.
  `analyze_similarities.py` found 345 gray-zone (0.75–0.85) pairs in
  `doc/similarity_analysis.md`, worth a human skim before treating 159 as
  final. `enrich_annotations.py` ran cleanly against the new file (0
  records needed annotating). `init_db.py`/`app/app.py` re-verified against
  the reloaded `h2regdocs`.
- **Follow-up fix, found by reviewing the gray-zone report (2026-09-07):**
  the first `znacka` pre-pass only *added* a merge guarantee (same `znacka`
  → same document) but never added the mirror guarantee (different
  non-empty `znacka` → **never** the same document, regardless of title
  similarity). This let genuinely distinct multi-part standards (e.g.
  `ČSN EN 62282-3-300` vs `-3-200`, `ČSN EN IEC 62282-2-100`) get clustered
  together for the LLM to adjudicate — nothing was actually corrupted in
  practice (the LLM correctly declined to merge them, "4 records in, 4
  out"), but that correctness depended on LLM judgment on that specific
  call, not on the code. Added an explicit veto: two records with
  different non-empty `znacka` can never be unioned by title-embedding
  similarity. A second pass then found the veto was *too* strict — it
  originally missed that `"ČSN EN 17127"` and `"EN 17127"` are the same
  standard (`ČSN` is just the optional Czech national-adoption prefix) and
  wrongly kept them as separate records; added `core_znacka()` to strip
  that prefix before both the deterministic pre-pass and the veto compare.
  Re-verified: `ČSN EN 17127` merges back to one record, the 5 distinct
  `62282-*` parts stay separate, reloaded into `h2regdocs` (159 records,
  unchanged from the count above since this fix only tightens correctness
  guarantees, not this particular corpus's outcome).
- **Follow-up #2, prompted by reviewing `similarity_analysis.md` itself
  (2026-09-07):** the report mixed two very different kinds of pairs —
  norms with genuinely different reference numbers (noise, now that
  different-`znacka` is a proven non-match), and a real, previously-invisible
  signal: **the same EU regulation cited twice, once in Czech and once in
  English** (Haltuf ingests both language versions as separate records).
  Root cause: `build_unified_db.py` hardcoded `"znacka": ""` for every
  Haltuf record — the reference number only ever lived in the title text
  itself (e.g. `"(EU) 2019/773 - TSI OPE - COMMISSION IMPLEMENTING
  REGULATION..."` vs `"...- Prováděcí nařízení Komise..."`). Fixed:
  - `extract_haltuf_znacka()` in `build_unified_db.py` pulls the leading
    reference-number token out of the title (147/179 Haltuf records now get
    a real `znacka`; the other 32 fail safely to `""`, i.e. no worse than
    before). Verified clean on the full Haltuf set before wiring in —
    every multi-record group it produced was a genuine same-instrument
    match (EN/CZ pairs, or literal duplicate source rows), zero
    false-positive groupings found.
  - `analyze_similarities.py` got the same different-`znacka`-excludes
    veto as `deduplicate_db.py` (duplicated as `core_znacka()`, not
    imported, to avoid triggering `deduplicate_db.py`'s API-key/logging
    setup as a side effect).
  - **Fixed a second incident-in-waiting the same day it was designed
    against:** `build_unified_db.py` still had zero memory of prior
    annotation-enrichment across a re-run (the exact bug that caused the
    near-miss above) — now loads the *existing* output file first and
    carries forward any `anotace_poznamka` a re-run's own sources don't
    themselves provide, keyed by `(zdroj_dat, nazev_cz)`. This closes the
    root cause permanently, not just this one recovery.
  - **Re-run results (superseded by follow-up #6/#7 below):** raw
    regeneration restored all 157 previously-lost annotations automatically
    (0 additional loss) and populated `znacka` for 147/179 Haltuf records.
    Deduplication now produces **139 records**
    (down from 159) — deterministic `znacka` matches jumped from 8 to 40
    clusters, 0 bad cross-`znacka` merges (checked programmatically), all
    5 distinct `62282-*` standard parts still correctly separate. The
    gray-zone report shrank from **345 to 78 pairs** (267 excluded as
    provably-different documents) — a direct, measured fix for the
    signal-to-noise complaint that prompted this. Reloaded into `h2regdocs`
    (139 records), app re-verified.
- **Follow-up #3 (2026-09-08):** extended `extract_haltuf_znacka()` with
  three more patterns, each verified against the *entire* Haltuf corpus
  (not just the misses) for zero regressions before wiring in: a trailing
  bracketed OJ-style reference (`"... [2019/795]"` — identical across
  languages, catches the EN/CZ UN/ECE Regulation No. 134 pair), a leading
  EU/ES act number with no dash separator (`"2014/34/EU \nDIRECTIVE..."`),
  and a Czech law citation `"č. NNN/YYYY Sb."` anywhere in the title
  (catches `"Zákon o ochraně ovzduší (č. 201/2012 Sb.)"`-style titles, where
  the number is a trailing parenthetical, not a leading token). Coverage:
  147/179 → **166/179** Haltuf records now get a real `znacka`. Re-run
  results: **137 final records** (down from 139), deterministic matches up
  to 45 (from 40), 0 bad merges, gray-zone report down to **66 pairs**
  (from 78). Reloaded into `h2regdocs`, app re-verified.
- **Follow-up #4 (2026-09-09):** applied the same idea to `Sinay_Zakony`,
  which had the exact same always-empty `znacka` bug (confirmed while
  checking `"458/2000 Sb."` in follow-up #3). Sinay's titles are prose,
  not leading-token (`"Nařízení Evropského parlamentu a Rady (EU)
  2022/869 ze dne ..."`), so `extract_haltuf_znacka()` was generalized into
  a single `extract_znacka_from_title()` used by both sources, adding: a
  Slovak `"č. NNN/YYYY Z. z."` law citation (mirroring the Czech `"Sb."`
  one, kept as a distinct suffix — CZ and SK are separate legal systems, a
  shared number must not collide) and an EU/ES/EÚ act number found
  *anywhere* in the text, not just leading (`EÚ`/`ES` normalized to `EU` so
  the same act cited under any of the three still compares equal). Verified
  zero regressions against Haltuf's full corpus before wiring in. Coverage:
  46/48 Sinay records now get a real `znacka` (the 2 misses have no
  reference number in the title at all — a bare strategy-document name and
  one Slovak "Vykonávacie rozhodnutie" citation with no `(EU)`/`Sb.`/`Z.
  z.` marker to anchor on).
  - **Re-run results:** **133 final records** (down from 137), 51
    deterministic merges and — notably — **0 semantic-only merges this
    run**: `znacka` coverage is now good enough that title-embedding
    similarity wasn't load-bearing for any actual merge in this corpus. 0
    bad merges (checked programmatically). `458/2000 Sb.` now correctly
    merges across `Sinay_Zakony` + `Haltuf_Dokumenty` into one record.
    Gray-zone report down to **54 pairs** (from 66). Reloaded into
    `h2regdocs`, app re-verified.
- **Known, disclosed limitation — not fixed:** 13/179 Haltuf records (the
  `RID` appendix pair — no digit to anchor on, and different appendices of
  the same treaty are genuinely different documents, same risk shape as the
  `62282-3-*` multi-part standards — plus empty-title junk rows) and 2/48
  Sinay records still get no `znacka`.
- **Follow-up #5, found by auditing the deduplicated output itself
  (2026-09-09):** a real correctness bug, not a naming-convention gap —
  scanning the 133-record output for any `znacka` value appearing on more
  than one final record found **7 values across 16 records that should
  have been 7**. Root cause: the deterministic pre-pass correctly grouped
  these into one cluster each (proven same document by exact reference
  number), but hand-off to the LLM lost that guarantee — `gpt-4o-mini`
  sometimes failed to actually collapse a cross-language (EN/CZ) pair or a
  very sparse (title-only, repeated many times) cluster into one record,
  even though nothing about *which* document it was was in question.
  Fixed in three parts:
  1. `validate_merge()` now also rejects an LLM merge that leaves two
     output records sharing the same `znacka` (previously only checked for
     an *invented* one), routing it through the same retry/escalate path.
  2. The retry loop was silently useless for this exact failure mode: at
     `temperature=0.0`, resending an identical prompt reproduces the same
     wrong output. Retries now include the specific rejection reason and a
     pointed correction instruction.
  3. **The real fix:** added `is_pure_znacka_cluster()` — when *every*
     record in a cluster shares the same core `znacka` (zero probabilistic
     judgment involved, unlike a mixed deterministic+semantic cluster),
     skip the LLM entirely and merge with new `programmatic_merge()`
     (longest title wins, list fields unioned, blank scalars backfilled
     from any member). There's no identity question left for an LLM to
     get wrong. Confirmed via a real run: two clusters that had failed all
     3 LLM retries (13-record `EN 17127` family, 6-record `2012/18/EU`
     pair) both merged correctly and instantly once routed here instead.
  - **Re-run results:** **0 remaining exact-`znacka` duplicates** in the
    output (verified programmatically). **123 final records.** Every one
    of this run's 51 merges went through the programmatic path — 0 LLM
    calls needed for merging at all this time (only embeddings), which is
    also a meaningful cost reduction. Record-accounting re-verified: 281
    raw → 11 no-title (excluded) + 270 accounted for across all audit-log
    clusters, matches exactly. Gray-zone report: 54 pairs (unchanged — this
    fix didn't touch clustering, only what happens after). Reloaded into
    `h2regdocs` (123 records), app re-verified.
- **Follow-up #6 (2026-09-09): resolved the `"ISO X"` vs `"ČSN (EN) ISO X"`
  ambiguity by querying the authoritative source instead of guessing.**
  Per domain guidance: a bare `"ISO X"` and its Czech national adoption
  (`"ČSN ISO X"` or `"ČSN EN ISO X"`, whichever form is current) are the
  same document in a different language and should merge — but `"ČSN ISO
  X"` and `"ČSN EN ISO X"` for the same number are two different *national
  adoption routes* that can't both be valid at once, so which is current
  needs checking against a real registry, not assuming.
  - Built `src/tools/check_csn_validity.py`, querying the free public
    catalog search at `csnonline.agentura-cas.cz/podrobne.aspx` (an
    ASP.NET WebForms POST with `__VIEWSTATE`/`__EVENTVALIDATION` handling)
    — this is the free catalog/metadata search, distinct from and NOT
    governed by the *paid* "ČSN online pro jednotlivce" subscription's
    Terms of Use (that document only restricts bulk PDF downloads from the
    authenticated full-text service). Rate-limited, for occasional
    targeted lookups, not a crawler.
  - **Confirmed against the registry** for all 3 pending groups: `ISO
    14687` → only `"ČSN ISO 14687"` exists (no EN variant at all,
    currently valid); `ISO 19880-1` → only `"ČSN ISO 19880-1"` exists (2
    editions: 2020 withdrawn 1.9.2025, 2025 currently valid); `ISO
    11114-1` → only `"ČSN EN ISO 11114-1"` exists (currently valid
    edition from 6.2021, several older withdrawn editions). **In all 3
    cases, the "ČSN EN ISO X" variant our data claimed to have doesn't
    exist in the registry at all** — meaning that designation in our raw
    source data (mostly Haltuf, one Prokop row) is itself a data-entry
    error, not a real second standard. Not silently corrected in the
    source files — flagging here rather than rewriting Prokop's/Haltuf's
    own "Značka"/title values based on an external source without asking.
  - **Found and fixed a real bug while investigating case 2 (`19880-1`):**
    `extract_znacka_from_title()`'s case C (leading code + dash) matched a
    dash with NO required surrounding whitespace, so a bare part-numbered
    code like `"ČSN EN ISO 19880-1"` was wrongly truncated to `"ČSN EN ISO
    19880"` — the internal hyphen in `-1` was mistaken for a prose
    separator. Fixed by requiring actual whitespace on both sides of the
    dash (verified against the same test cases as follow-up #3/#4, zero
    regressions). Re-ran the full pipeline: **122 final records**, 0
    duplicate-`znacka`, 0 bad merges, record-accounting re-verified
    (281 = 11 no-title + 270 clustered). Reloaded into `h2regdocs`, app
    re-verified.
- **Follow-up #7 (2026-09-09): wired `check_csn_validity.py` into
  `deduplicate_db.py` as an automated pipeline step**, plus a refactor for
  testability and a full unit test suite (`tests/test_build_unified_db.py`,
  `tests/test_deduplicate_db.py`, 44 tests total). This is a concrete,
  working instance of §3.2's Research Agent pattern — tool-calling an
  external source to fill a gap our own data can't resolve, never
  auto-merging without a clear, single, confirmed answer.
  - `deduplicate_db.py`'s inline clustering code was extracted into a
    standalone `build_clusters(valid_data, similarity_threshold)` — pure,
    independent of the OpenAI embeddings call, unit-testable with
    synthetic vectors instead of hitting the network.
  - New `find_iso_csn_ambiguous_groups()` (pure) + `resolve_iso_csn_ambiguity()`
    (injectable `csn_search` callable, defaults to a real rate-limited
    lookup): after the main merge loop, groups final records by bare digit
    core (`digit_core()`) where `core_znacka` still differs and at least
    one mentions "ISO", queries the registry for `f"ISO {core}"`, and
    merges the group under the registry's confirmed designation **only
    when exactly one currently-valid designation is found** — a lookup
    failure, no match, or more than one valid designation (contradicting
    "only one can be valid at a time") leaves the group untouched with a
    new audit-log entry (`csn_lookup_failed` / `csn_lookup_inconclusive` /
    `merged_by_csn_registry`) for a human to look at instead. Wrapped in a
    try/except in `main()` too — a total failure of this step (e.g.
    `requests`/`bs4` missing) logs a warning and never blocks the rest of
    the pipeline.
  - Found and fixed a small cosmetic bug while verifying this end-to-end:
    `programmatic_merge()`'s `zdroj_dat` field wasn't splitting an
    already-comma-joined value from a prior merge before deduplicating,
    so re-merging across previously-merged clusters (exactly what this new
    step does) could produce `"Prokop_Normy, Haltuf_Dokumenty, Prokop_Normy"`.
    Fixed to split on `", "` first.
  - **Re-run results:** the registry confirmed and merged all 3 pending
    groups from follow-up #5/#6 (`ISO 14687` → `ČSN ISO 14687`, `ISO
    19880-1` → `ČSN ISO 19880-1`, `ISO 11114-1` → `ČSN EN ISO 11114-1`) —
    exactly matching the manual verification done earlier in chat, now
    automatic on every future run. **119 final records** (down from 122),
    0 duplicate-`znacka`. Reloaded into `h2regdocs`, app re-verified.
  - **Test suite:** `tests/test_build_unified_db.py` covers every
    `extract_znacka_from_title()` pattern found this session (leading
    dash-separated, bare code, no-separator EU number, trailing OJ
    bracket, Czech `Sb.`/Slovak `Z. z.` citations with messy spacing,
    EU/ES/EÚ normalization, the amends-vs-own-number precedence, the
    part-number-dash regression, the no-false-positive-on-`RID` case).
    `tests/test_deduplicate_db.py` covers `normalize_znacka`/`core_znacka`/
    `digit_core`, `validate_merge` (both rejection modes), 
    `is_pure_znacka_cluster`, `programmatic_merge`, `match_type_for_group`,
    `build_clusters` (synthetic embeddings — same-znacka-despite-dissimilar
    -titles, different-znacka-vetoes-identical-embeddings, semantic
    fallback, one-sided-znacka-doesn't-veto), the new ISO/ČSN resolution
    functions (mocked registry), and `deduplicate_cluster_with_llm`
    (mocked OpenAI client: first-try success, retry-with-corrective
    -feedback, all-retries-exhausted, API-exception-retried). Also fixed
    the pre-existing `tests/test_search.py`, which hardcoded an exact
    title string that a since-improved merge decision legitimately
    changed — rewritten to match by law number instead of exact title
    text, so it survives future title-selection changes.
- **Follow-up #8 (2026-09-09): two previously-unparsed Sinay raw sources.**
  `data/20250712_Sinay/raw/Zoznam_noriem_vodik-11_02_2025.pdf` (84-page,
  gridline-less 4-column export of Slovak/foreign standards) and
  `.../Zoznam_noriem_Vodik_Road_map_Nemecko_Priradenie_STN_VERZIA_2024_06_27b.xlsx`
  (German H2 standardization roadmap, ~960 rows) were never processed.
  New `src/tools/parse_sinay_norms.py`:
  - PDF: no table gridlines, so pdfplumber's own detection found nothing —
    reconstructed the table from word x-position clustering into 4 columns,
    with row boundaries anchored on the Designation column. Two bugs found
    and fixed before trusting the output: long designations wrapping their
    trailing `YYYY.MM` onto a second line were creating bogus empty-title
    rows (merged back into the previous designation), and wrapped URLs
    were getting a stray space inserted mid-string (stripped).
  - **980 PDF + 969 XLSX = 1949 records**, schema matching
    `data/20250303_Prokop/normy_vodik.json` (this is norms content, not
    laws) plus one new field: **`Jurisdikce`** — this source is majority
    Slovak (STN) and German norms, which are NOT valid in Czechia just
    because they share an EN/ISO ancestor with a ČSN (explicit user
    guidance). `classify_jurisdikce()` derives it from the designation/
    issuing-body text (STN→SK; DVGW/DIN/VDI/DASt/DGUV/BVEG/BAuA→DE;
    ISO/IEC→mezinárodní; CEN/CENELEC/EIGA/bare-EN-number→EU;
    ASTM/ASME/API/CGA/ANSI/...→US; CSA→CA; BSI→UK; AFNOR→FR; NEN→NL; else
    `"neurčeno"` — fails safe rather than guesses). Distribution: 758 SK,
    383 DE, 345 mezinárodní, 205 neurčeno, 148 US, 99 EU, 5 CA, 4 FR, 2 UK.
  - Output: `data/20250712_Sinay/sinay_normy_processed.json`. Not wired
    into `build_unified_db.py` at this point — see follow-up #9.
- **Follow-up #9 (2026-09-09): wired Sinay_Normy into the pipeline, and
  found a real cross-jurisdiction merge bug doing it.**
  - `build_unified_db.py` gained a 4th source branch (`Sinay_Normy`) and a
    `jurisdikce` field on every record: `"CZ"` for Prokop (unambiguous —
    these are ČSN norms), per-record from the parser for Sinay_Normy, left
    unset (`""`) for Sinay_Zakony/Haltuf (both mix jurisdictions per
    record with no reliable per-row marker of their own — not confidently
    classified without deeper work than was asked for here).
  - `deduplicate_db.py`'s `build_clusters()` (both the deterministic and
    semantic passes) and `is_pure_znacka_cluster()` now veto a merge
    whenever two records have a **known, differing** jurisdikce — e.g. a
    Slovak STN and a Czech ČSN adoption of the same EN standard share a
    core `znacka` but must never become one record. An unset/`"neurčeno"`
    jurisdikce on either side never blocks a match — only two *known*,
    *different* values do.
  - **Bug found in a real run, before it reached the database:**
    `resolve_iso_csn_ambiguity()` (follow-up #7) predates `jurisdikce` and
    had no awareness of it — it grouped by bare digit-core only, so it
    merged a **Slovak STN amendment record into a Czech ČSN record**
    (`STN EN ISO 11114-1/Zmena` into `ČSN EN ISO 11114-1`) and mislabeled
    some purely-foreign draft-standard clusters (no CZ record at all) with
    a `"ČSN ..."` designation as if one of them were the actual Czech
    standard. Caught by inspecting the audit log before running
    `init_db.py` — restored the pre-run backup, fixed
    `find_iso_csn_ambiguous_groups()` to exclude any record with a known
    non-CZ jurisdikce from consideration entirely (this function's whole
    job is resolving presumed-CZ ambiguity; a foreign norm having a
    matching CZ standard is a cross-reference fact, never a merge — see
    below), re-ran clean. **Lesson:** every merge-capable code path needs
    the jurisdiction guard independently: build_clusters, is_pure_znacka_
    cluster, AND resolve_iso_csn_ambiguity all had to be checked — adding
    a new field doesn't retroactively protect code written before it.
  - **Second, smaller bug found in the same pass:** the Sinay PDF uses
    `-` and `–` (en dash) interchangeably for the same date separator
    (e.g. `"STN EN ISO 11114-1/ – 2020.12"` vs `"...  / - 2020.12"`),
    silently defeating exact-`znacka` deduplication. Fixed in
    `normalize_znacka()` (dash-variant folding).
  - New `src/tools/check_foreign_norm_csn_equivalents.py` — the actual
    "does the SK/DE norm have a ČSN equivalent" cross-reference: for every
    SK/DE-jurisdiction record with an ISO/EN-style core, queries the ČSN
    registry (deduplicated to unique queries first — 644 candidate records
    collapsed to 332 unique queries) and reports whether exactly one
    currently-valid ČSN designation exists. **This is deliberately a
    report, never a merge** — `data/20250712_Sinay/sinay_normy_csn_equivalents.json`,
    not a database write. Results: 299/332 (covering 571 source
    designation variants) have a confirmed, currently-valid ČSN
    equivalent; 23 ambiguous (2+ valid ČSN designations — needs a human
    look); 10 found in the registry but not currently valid.
  - `analyze_similarities.py` got the same jurisdikce veto as
    `build_clusters`, and — necessary at this corpus size — both vetoes
    were moved to run *before* the expensive `cosine_similarity` call
    instead of after (2219 valid records ⇒ ~2.46M pairs; computing
    embedding dot-products for all of them instead of skipping
    cheaply-vetoed ones first was the difference between finishing in
    under a minute and a 5+ minute run that had to be killed and restarted
    once already this session).
  - **Re-run results:** 2230 raw records (up from 281 — the new source
    dominates) → **1344 final deduplicated records**. Gray-zone report:
    345 → 57 pairs (2,450,524 excluded by the znacka veto, 8 by the
    jurisdikce veto specifically — confirming the two vetoes catch mostly
    overlapping but not identical cases). Reloaded into `h2regdocs` (1344
    records), app re-verified. New tests added for the jurisdiction veto
    (including a direct regression test reproducing the STN-into-ČSN bug)
    and the dash-normalization fix; 55 tests total, all passing.
  - **Known, disclosed residual:** 2 exact-`znacka` duplicate pairs remain
    (e.g. `"ASTM F1624-12"` appears once from Prokop tagged `"CZ"` and once
    from Sinay_Normy tagged `"US"`). This is the jurisdiction veto correctly
    erring safe, not a bug: Prokop's own `Značka` column occasionally cites
    a foreign standard directly (no `ČSN`/`STN` national-adoption prefix at
    all), so the blanket `Prokop→"CZ"` assignment is imprecise for those
    specific rows — fixing it precisely would need the same per-record
    classification logic as `classify_jurisdikce()`, applied to Prokop's
    own data too. Narrow (2 pairs total), not chased further.
- **Broader design point raised during review, not implemented:** cosine
  similarity over bare titles is inherently weak for terse/technical titles
  that share domain vocabulary; it would be stronger run over
  title+`anotace_poznamka` (when present) instead of title alone. Would
  change both `deduplicate_db.py`'s clustering and
  `analyze_similarities.py`'s gray-zone report — flagged as a real
  follow-up rather than assumed.
- **Near-miss caught during this run:** re-running `build_unified_db.py` as
  a sanity check for the path fix silently wiped `anotace_poznamka` on 157
  of 281 records — that script's own logic always blanks Sinay annotations
  and only reads Prokop's own `Anotace` field, neither of which accounts
  for whatever earlier, untracked process had enriched the existing raw
  file. Caught via a pre-emptive backup diff and restored before any
  further step ran. **Lesson recorded here so it isn't rediscovered the
  hard way:** `build_unified_db.py` is not safe to re-run casually — always
  back up `data/database_merged_raw.json` first.

### Step 2 — Load into the real schema

- Write the field mapping from Pipeline A's vocabulary (`nazev_cz`, `znacka`,
  `typ_dokumentu`, …) to `Document` / `DocumentType` / `DocumentSource` /
  `Keyword` / `DocumentVersion` in MariaDB, populating the new `identifier`
  column (added in the Konsolidace schema) from `znacka`.
- This is the step that has never actually happened: it is what turns the
  JSON exercise into an actual queryable database.

### Step 3 — Populate process layers B–D

- Populate process layer B from the V02 text (separate, larger effort —
  analytical extraction, not just scripting), then layer C links and layer D
  compliance scaffolding, per the migration plan already written in
  `Konsolidace-DB-popis.md` §9. (The schema itself is already in place from
  Step 0 — this step is about content, not DDL.)

## 3. Agentic architecture for ongoing operations

**Reconciliation note (2026-09-07):** an earlier draft of this section was
5 flat bullets that only partially reflected
`doc/automation_proposal/Automating Hydrogen Legislation Database
Consolidation.md`. That proposal (a Gemini transcript, not something this
project wrote) specifies a concrete multi-agent architecture — LangGraph
`StateGraph`, named agents, a retry/escalate loop, specific model
assignments, and a richer extraction schema. This section replaces the flat
bullets with that architecture, adapted to what actually exists in this
repo (the `Document`/`identifier` column from Step 0, `znacka` as
`reference_number`, `search_agent.py`, `deduplicate_db.py`). Nothing in
this section is built yet — it is a design, not a completed step.

### 3.1 Why agents, not more scripts

The current enrichment scripts (`enrich_eu_laws.py`, `process_laws.py`,
`enrich_annotations.py`) are one-shot LLM calls with no verification, no
retry, and no shared state — exactly the failure mode that produced the
untrustworthy 281→165 dedup run (§1). The proposal's fix is a **deterministic
state machine**, not a chat between agents: LangGraph is the primary
framework (CrewAI/AutoGen are explicitly the wrong tool here — they're built
for open-ended agent conversation, not rigid schema-validated pipelines).

### 3.2 The agent roster, mapped onto this repo

| Agent | Function | Replaces / extends | Model (proposal's recommendation) |
|---|---|---|---|
| **Parser** | VLM layout parsing of raw PDFs/scans into clean Markdown before extraction. | Nothing today — Pipeline A only ever consumed pre-parsed Excel/JSON. Needed for §3.3 item 1 (EUR-Lex/e-Sbírka source screening will return raw PDFs). | LlamaParse or Docling/Marker (not OCR). |
| **Extraction** | Pulls structured fields into a schema-validated JSON object. | `enrich_eu_laws.py` / `process_laws.py` / `enrich_annotations.py`. | Claude Sonnet or Gemini Pro (schema adherence, long-context). |
| **Verification** | Rejects any extraction whose `verification_evidence` quotes don't appear verbatim (normalized) in the source. | Nothing today — this is the gate none of the enrichment scripts have (§1). | Same model as Extraction; logic is deterministic Python (`verify_evidence()`/`normalize_text()`), not a second LLM call. |
| **Reconciliation** | Deterministic `reference_number` match first, semantic/embedding fallback second; never auto-merges, only flags. | `deduplicate_db.py`'s dedup logic — Step 1's `znacka` pre-pass is this agent's deterministic branch; `reference_number` = `znacka` = the new `Document.identifier` column. | OpenAI o1/o3 or equivalent reasoning model for the ambiguous cases only. |
| **Research** | Tool-calls EUR-Lex/e-Sbírka APIs to fill gaps (missing dates, etc.), triggered only when a field is null after verification. | `search_agent.py` (currently generic DuckDuckGo search — ongoing-ops item 1 below already called for replacing this with direct API tool-calling). | GPT-4o or Claude Sonnet with `bind_tools`. |

### 3.3 The pipeline (LangGraph `StateGraph`)

1. **Source screening.** Query EUR-Lex / e-Sbírka / ČAS APIs directly (not
   generic web search) for new/changed documents. Output: candidate files
   queued for ingestion, never auto-inserted. *(unchanged from the prior
   draft of this section)*
2. **Parse → Extract.** Parser Agent normalizes the raw file; Extraction
   Agent outputs a schema-validated object (§3.4) including a mandatory
   `verification_evidence` array of verbatim source quotes.
3. **Verify.** `verify_evidence()` checks every quote against the
   normalized source text. Failure routes back to Extraction with the
   specific failed quotes appended to the retry prompt — capped at 3
   attempts, then `escalate` (human review), never a silent pass-through.
   This is the direct fix for the silent-failure bug already flagged for
   `deduplicate_db.py` in Step 1.
4. **Research (conditional).** Only runs if verified data still has null
   fields the tools can fill (e.g. missing `publication_date`).
5. **Reconcile.** Exact match on `identifier`/`reference_number` first;
   embedding/title-similarity fallback second (this is Step 1's ordering,
   now run per-candidate against the *live* database instead of as a
   full-corpus batch sweep). A match never overwrites — see item 4 below.
6. **Human-in-the-loop.** Every `escalate` or `flagged_for_review` outcome
   needs a real destination: a review flag on the record plus a small admin
   view in the Flask app, not a dead-end concept.

Two items from the prior draft still apply unchanged and aren't part of the
proposal's own design (they're specific to this project's schema):

- **Updates vs. duplicates.** A Reconciliation match against an existing
  `identifier` should create a new `DocumentVersion` (using the schema's
  `is_current` flag), not a new `Document` row — an amendment is a version,
  not a duplicate.
- *(HITL destination is folded into pipeline step 6 above.)*

### 3.4 Schema gap this architecture exposes

The proposal's extraction schema includes `hydrogen_specifics` (`focus_areas`,
`hydrogen_definitions` enums, `key_obligations`) and `legal_relationships`
(`transposes_eu_directive`, `amends_legislation`) — **none of this has a
column anywhere in `Konsolidace-DB-schema.sql`'s layer A** (verified: the
layer-A `ALTER`s only add `identifier`, `institution_type`, `jurisdiction`,
`is_current`). Adopting this extraction schema means either:

- adding normalized lookup + link tables in the Konsolidace style (e.g.
  `hydrogen_focus_area`, `document_focus_area`, and a `document_relationship`
  table for `TRANSPOSES`/`AMENDS`/`REPEALS`), consistent with how layers B–D
  already model enums as separate value tables, or
- a single `Document.metadata_json` JSON column as a faster interim step.

Not decided yet — see §4.

### 3.5 Why `verification_evidence` isn't implemented as literally specified

The proposal's anti-hallucination mechanism assumes the Extraction Agent
receives full source-document text to quote from. **None of this repo's
scripts ever have that.** `deduplicate_db.py`, `enrich_eu_laws.py`,
`enrich_annotations.py`, and `process_laws.py` only ever operate on
structured spreadsheet metadata (titles, dates, keyword lists) supplied by
partners — there is no raw legislative text anywhere in `data/` to check a
quote against. Building genuine verbatim-quote verification needs the
Parser Agent plus real document fetching, which §4 defers along with the
rest of the LangGraph architecture.

What was actually implemented instead, in the same anti-hallucination
spirit but scoped to what these scripts really do (Step 1, above):
`deduplicate_db.py`'s merge task is reconciling *structured records*
against each other, not extracting facts from a document — so its
equivalent guardrail is a **structural sanity check**: reject any merge
that invents a `znacka` absent from every input record. `enrich_eu_laws.py`
and `enrich_annotations.py` keep only their existing "NEHALUCINUJ" prompt
instructions; no verbatim check was bolted onto them, because there is
nothing to check it against. This is a stated limitation, not a gap that
was silently dropped.

## 4. Open decisions

- ~~Engine (SQLite vs. MariaDB)~~ — **resolved: MariaDB**, database name
  `h2regdocs`, credentials in a repo-root `.env` (git-ignored, confirmed in
  place).
- ~~Confirm whether Step 0 should be executed immediately, standalone~~ —
  **resolved: yes**, executed 2026-09-07 (see Step 0 above for deviations
  found along the way).
- ~~Scope check for the agentic architecture (§3)~~ — **resolved: harden
  existing scripts only** (Step 1, above). No LangGraph adoption, no live
  EUR-Lex/e-Sbírka source screening, no PDF-parsing sub-layer this pass —
  all explicitly deferred to a later, separately-scoped pass.
- ~~Orchestration framework~~ — **resolved: not adopted this pass** (follows
  from the scope decision above). LangGraph remains the recommendation
  *when* the full §3 architecture is eventually built; Step 1 borrows only
  the patterns (retry cap, deterministic-then-semantic ordering) in plain
  Python.
- ~~Model provider~~ — **resolved: OpenAI only** (`gpt-4o`/`gpt-4o-mini`,
  matching what's already wired via `.openapi_key`). No Anthropic/Google
  keys exist in this repo or were provisioned; revisit per-role model
  choice only if OpenAI-only proves insufficient.
- ~~Document-parsing sub-layer~~ — **resolved: moot for now**, follows from
  the scope decision — no live PDF ingestion is being built this pass. Will
  need its own decision when source screening (§3.3 item 1) is actually
  built.
- ~~Schema extension for `hydrogen_specifics`/`legal_relationships`~~ —
  **resolved: normalized lookup tables** (Konsolidace style, e.g.
  `hydrogen_focus_area`, `document_focus_area`, `document_relationship`),
  matching the schema's existing 100%-normalized convention (confirmed: zero
  JSON columns anywhere in `Konsolidace-DB-schema.sql`). Not built this
  pass — moot until the extraction schema itself is adopted (also deferred).
