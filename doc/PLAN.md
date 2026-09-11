# Database Consolidation & Automation Plan

**Project:** NAHYC DP004 — Vodíkový technologický inkubátor
**Date:** 2026-09-07
**Status:** Steps 0, 1, 2 and 3a executed 2026-09-07–2026-09-10 (4th
source `Sinay_Normy` — Slovak/German norms — wired in with a
jurisdiction-aware dedup guard; MariaDB `h2regdocs` now holds 1217
`Document` rows — 1194 from the pipeline + 23 from V02's bibliography —
plus a fully-loaded process layer B, U1–U7, from `doc/NAHYC DP004 V02 -
Popis procesů.docx`). §4 (full-text acquisition for laws + source
screening) designed and implemented 2026-09-09; the full corpus was
fetched 2026-09-11 (140/144 downloadable law records, 105 MB). Step 3b
(layer D — compliance pathway) was designed 2026-09-10 (full findings +
exact input shape recorded below) then **postponed at the user's explicit
direction** — current priority is the regulatory-document database
itself: Step 1 follow-ups #10–#13 (2026-09-11) found and fixed seven real
missed-duplicate/parsing/classification bugs via a systematic
duplicate-title audit (1344→1200→1196→1194 records; only 1 of the
original 2 known cross-jurisdiction `identifier` collisions remains —
the other turned out to be a classification bug, not a genuine
cross-jurisdiction duplicate). Two items flagged for the user's own
manual resolution rather than guessed (`CSA ANSI GSV 4.1`, `SAE J2601
/1`); follow-up #14 confirmed `TRBS 3151`/`TRGS 751` as one document
published under two official designations (a German *Verbundregel*) —
a genuine schema gap (no place for a second identifier), not resolved
yet. A dedicated review/cross-check working mode for the database
interface is a flagged future need, not designed yet. The agentic
architecture in §3 remains a
proposal.
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
- **Follow-up #10 (2026-09-11): found and fixed a real missed-duplicate
  bug while auditing the corpus for exact-once representation** (per the
  user's decision, 2026-09-10, to postpone Steps 3b/§3 and focus on the
  regulatory-document database itself). Checking for exact-duplicate
  normalized titles under different `znacka` values (145 cases) found
  three categories:
  - **81 cases: a real normalization gap, fixed.** `normalize_znacka()`
    folded dash variants but never stripped the Sinay parser's trailing
    edition-date suffix (`"ISO 16111"` vs `"ISO 16111/ - 2018.08"` — the
    same standard, one raw record keeps the date, one doesn't) — so these
    silently failed to merge. Fixed by adding `_EDITION_DATE_SUFFIX_RE`
    (`/\s*-\s*\d{4}\.\d{2}\s*$`, requiring the `.MM` month component so a
    real identifier ending in a bare year, e.g. `"ADR 2025"`, is never
    touched) to both `deduplicate_db.py` and `analyze_similarities.py`'s
    (duplicated, side-effect-free) `core_znacka()`. Deliberately does
    **not** strip an amendment marker before the date (`"...+A1/ -
    2024.02"` keeps its `+A1`) — see the next bullet.
  - **11 cases: base-standard vs. its amendment** (e.g. `STN EN 13445-2`
    vs. `.../A1`) — arguably the same document across time (what
    `DocumentVersion` exists for), currently two separate `Document` rows.
    **Deferred to a separate pass per the user's explicit decision** —
    the fix above verified to leave these correctly un-merged (regression
    test: `test_normalize_keeps_amendment_marker_before_the_date`).
  - **53 "other" cases**: a mix, mostly legitimate (cross-jurisdiction
    adoptions of the same IEC/EN standard, e.g. Slovak STN vs. German DIN,
    already correctly kept separate by the jurisdikce veto) or
    designation renumbering over time — not chased further this pass.
  - **Re-run results**: `deduplicate_db.py` → **1200 records** (down from
    1344 — matches the 145-title-collision finding closely), 2 known
    cross-jurisdiction `identifier` collisions unchanged (`ASTM F1624-12`,
    `DIN EN 10216-2`), 0 new bad merges. One new cluster (bare `ISO 14687`
    vs. its two differently-dated Sinay editions vs. `ČSN ISO 14687`) is
    *not* a pure-znacka cluster (`CZ` + `mezinárodní` are both "known"
    jurisdictions per `_jurisdikce_known`), so it went to the LLM path,
    which couldn't fully collapse it — correctly flagged in
    `dedup_review_queue.json` rather than guessed. `analyze_similarities.py`
    re-run: gray-zone pairs 57→62, but "excluded for jurisdikce conflict"
    jumped 8→1057 and "excluded for different znacka" dropped slightly —
    expected: many same-title pairs were previously hidden behind the
    znacka-veto for the wrong reason (date-suffix noise, not a real
    difference) and now correctly reach the jurisdikce-veto instead.
    `init_db.py`/`load_process_layer.py` reloaded (1223 `Document` rows —
    1200 pipeline + 23 bibliography from Step 3a — `DocumentVersion` 1:1,
    layer B/`node_document` unchanged). 3 new regression tests, 168 total
    at this point. `app/app.py` re-verified.
  - **Known, disclosed limitation, not new**: this pass did not attempt
    the 11 amendment pairs or the 53 "other" cases — see above.
- **Follow-up #11 (2026-09-11): analyzed the remaining "other" duplicate-
  title cases (49, re-counted post-fix-#10) and fixed three more real,
  narrow bugs found in that analysis** (a fourth category — ISO/IEC
  draft-vs-final designation pairs, 23 groups — and a fifth — ambiguous
  body/series renaming, ~9 groups — were left for the amendment-pairs-style
  deferred pass; a sixth, ~4 groups, are coincidental generic-title
  collisions between genuinely different documents, not a bug):
  - **A real bug: "no designation available" placeholder text taken
    literally as a znacka.** The Sinay PDF/XLSX sources sometimes write
    an explicit placeholder ("bez označenia" / "keine Nummer vorhanden")
    into the designation cell instead of leaving it blank — taken
    literally, two records both saying "no number available," in
    different languages, were treated as two different *known* znacka
    values, blocking an otherwise-legitimate same-title merge. Affected
    **34 records** corpus-wide (17+17), not just the 1 pair that first
    surfaced it. Fixed in `parse_sinay_norms.py`
    (`is_placeholder_designation()`, wired into both the PDF and XLSX
    paths) — these now correctly get an empty znacka. Also had to fix the
    XLSX row-drop condition, which used to gate on "has a znacka" — a
    title-bearing row with only a placeholder designation is legitimate
    content (a real industry guidance document, just with no formal
    standard number) and must not be silently dropped just because
    `znacka` ends up empty; the gate now matches `parse_pdf`'s own
    title-only convention.
  - **A real parsing-truncation bug.** A long designation wrapping onto a
    second visual line was only special-cased for a bare "YYYY.MM" date
    continuation (`_DATE_FRAGMENT_RE`, from follow-up #8) — a *non-date*
    wrapped tail (e.g. "Sandia Report SAND2012-" / "7321" on the next
    line, "UL Standard (UL 125, Edition" / "1)") fell through and was
    silently dropped, truncating the designation. Root-caused against the
    actual PDF word positions (confirmed: the missing text really is
    present, one line down, at the same left margin as the designation
    column — not missing from the source, just not merged back). Fixed
    with a second, narrow continuation pattern
    (`_SHORT_CONTINUATION_RE`: a short digits/closing-punctuation-only
    line is never the start of a new designation). Refactored the merge
    logic out into a standalone `merge_designation_continuations()` for
    direct unit testing. Fixed **8 cases** in the PDF source (more than
    the 5 first spotted via duplicate titles — 3 more had no XLSX
    counterpart to surface them that way, e.g. "UL Standard (UL 119,
    Edition 10)"). One structurally different, genuinely ambiguous case
    ("AGBF- Leitfaden – Wasserstoff" / "und dessen Gefahren") was left
    unfixed — its PDF layout has the same text duplicated across the
    designation *and* title columns in a way that doesn't fit this
    pattern; forcing a fix there risked new false merges elsewhere.
  - **Trivial separator-formatting variants**: `"CSA/ANSI"` vs.
    `"CSA ANSI"`, `"IGEM/TD/1"` vs. `"IGEM TD1"` — added a short, explicit
    allowlist (`_KNOWN_SERIES_SEPARATOR_RES` in `deduplicate_db.py`,
    mirrored in `analyze_similarities.py`) that folds separators only for
    these two known series names — deliberately not a blanket
    "remove every slash" rule, which would risk conflating genuinely
    different designations elsewhere (e.g. `"STN CLC/TR ..."` vs.
    `"TNI CLC/TR ..."`, a real but different, deferred question).
  - **Re-run results**: full pipeline re-run (`parse_sinay_norms.py` →
    `build_unified_db.py` → `deduplicate_db.py` → `analyze_similarities.py`
    → `init_db.py` → `load_process_layer.py`). Raw corpus 2230→2225,
    deduplicated **1200→1196 records**, 0 new bad merges, **0 items in
    `dedup_review_queue.json`** (down from 1 — the ISO 14687 cluster now
    fully auto-resolves: `"ISO 14687"` international vs. `"ČSN ISO
    14687"` Czech, correctly separate, no jurisdiction violation). Known
    2 cross-jurisdiction `identifier` collisions unchanged. 14 new tests
    (186 total). `h2regdocs` reloaded (1219 `Document` rows), `app/app.py`
    re-verified. Remaining "other" duplicate-title groups after this pass:
    18 (down from 49) — all correctly belonging to the deferred
    draft-stage/renaming categories or genuine title coincidences, not
    further bugs.
- **Follow-up #12 (2026-09-11): analyzed all 18 remaining "other" groups
  in detail (cross-checking the `anotace_poznamka` text, identical
  between pairs in most cases — strong independent confirmation of which
  pairs really are the same document) and fixed two more real bugs found
  there.**
  - **A systemic `classify_jurisdikce()` ordering bug, bigger than the
    audit alone suggested.** `STN` was already checked first (so a
    Slovak adoption's own catalog entry citing an international
    committee never overrides its SK jurisdiction) — but the German
    marker group (`DVGW`/`DIN`/`VDI`/...) was checked *after* the
    international ISO/IEC/CEN/EIGA group instead of getting the same
    precedence. A German (`DIN`-prefixed) standard's catalog entry
    routinely cites the international/European committee that
    originated it (e.g. `"DIN EN IEC 60079-11"` filed under `"IEC/TC
    31"`, `"DIN EN 10216-2"` filed under `"CEN/TC 459/SC 10/WG 1"`), so
    it was being misclassified `mezinárodní`/`EU` instead of `DE`.
    Checked the *whole* corpus, not just the audit's 18 cases: **45
    records** affected. Fixed by moving the German marker group to right
    after `STN` in `_JURISDICTION_MARKERS` — verified safe first: none
    of the 26 correctly-SK records that also cite a German mirror
    committee flip, since `STN` still wins ahead of it. Concrete payoff:
    `"DIN EN 10216-2"` (previously split `DE`/`EU` across two rows,
    genuinely the same document per its own `anotace_poznamka`) now
    merges into one record; the other 44 fixes are jurisdikce-accuracy
    corrections with no merge of their own, but keep the field correct
    for whatever queries/filters eventually run against it.
  - **A second edition-year suffix style**: `"ISO 11413 :2019"` (bare
    colon-year, no month) vs. `"ISO 11413/ - 2019.03"` (the more common
    Sinay `"/ - YYYY.MM"` form) — same standard. Added
    `_COLON_YEAR_SUFFIX_RE` alongside the existing edition-date-suffix
    regex, careful to require a *4-digit* year right after the colon so
    the corpus's own `"part:2-digit-year"` citation convention
    (`"CHMC 2:19"`, `"CSA HPIT 1:15 (R2020)"`) is never touched.
  - **Re-run results**: full pipeline re-run. Deduplicated **1196→1194
    records** (the two fixes above merging exactly one pair each), 0 new
    bad merges, review queue still empty, only the one already-known
    `ASTM F1624-12` cross-jurisdiction `identifier` collision remains (2
    known collisions → 1 — `DIN EN 10216-2` is no longer one, since it
    was a mislabeling, not a genuine cross-jurisdiction case). 6 new
    tests (190 total). `h2regdocs` reloaded (1217 `Document` rows),
    `app/app.py` re-verified.
  - **Flagged for manual resolution, not auto-fixed — `CSA ANSI GSV 4.1`
    vs. `CSA ANSI HGV 4.1`.** Identical `anotace_poznamka`, and per the
    user's own check against the CSA store (2026-09-11): no `"GSV"`
    standard exists there (only `CSA/ANSI LNG 4.1` and `CSA/ANSI NGV
    4.1`) — "GSV" is very likely a data-entry typo for "HGV" in one raw
    source row, but not confirmed enough to silently rewrite a
    designation. Also note (same source): the corpus consistently omits
    the "/" CSA itself uses in its own branding (`"CSA/ANSI"`, not `"CSA
    ANSI"` — already handled for matching purposes by follow-up #11's
    separator fold, but the *stored* designations remain un-rewritten,
    matching this pipeline's general practice of normalizing only for
    comparison, not silently rewriting source values). **Separately
    flagged by the user**: the whole `CSA/ANSI HGV *` citation list in
    this corpus may itself be outdated — needs checking against
    <https://www.csagroup.org/store/search-results/?search=HGV> before
    trusting any of these designations/editions as current. Not done in
    this pass.
- **Follow-up #13 (2026-09-11): re-checked the (now 14) remaining "other"
  duplicate-title groups after follow-up #12's fixes — one of them
  resolved itself:** `"STN EN 60079-7"` vs. `"DIN EN IEC 60079-7"`
  previously showed as `SK` vs. `mezinárodní` (ambiguous); now correctly
  `SK` vs. `DE` — a Slovak and a German national adoption of the same
  IEC standard, unambiguously two separate documents, not a duplicate at
  all. Direct confirmation the ordering fix works as intended. The other
  13 groups are unchanged from follow-up #11's categorization (renaming/
  draft-stage/ambiguous-source-labeling/coincidental-title/already-
  flagged/already-disclosed) — nothing new to fix.
  - **SAE J2601 research, recorded for the future norm-searching/
    downloading work this project will eventually need (per the user,
    2026-09-11) — not acted on in the corpus yet:**
    - Authoritative source for SAE standards: <https://www.sae.org/standards>.
    - `SAE J2601` ("fueling protocols for light duty gaseous hydrogen
      surface vehicles") has a real family of related, but DIFFERENT,
      standards: `J2601/2` (heavy-duty vehicles), `J2601/3` (industrial
      trucks), `J2601/4` (ambient-temperature variable/fixed-orifice
      protocols for light-duty vehicles), `J2601/5` (high-flow
      prescriptive protocols for medium/heavy-duty vehicles). **There is
      no `J2601/1`** — per the user's own check of SAE's site, our
      corpus's `"SAE J2601 /1"` is most likely just a citation of the
      base `J2601` itself, not a real distinct part. Not confirmed
      enough to merge automatically (a guess, not a fact) — left as-is,
      same as the CSA case above.
    - **SAE itself is inconsistent about the separator** between the
      base number and the part number — both `"J2601/2"` and `"J2601-2"`
      are used for the same standard. `"SAE J2601/2"` and `"SAE
      J2601/3"` are already in this corpus (confirmed genuinely
      different documents — "Fueling Protocol for Gaseous Hydrogen
      Powered Heavy Duty Vehicles" / "...Industrial Trucks" respectively,
      matching the family list above) — groundwork for a future
      `_KNOWN_SERIES_SEPARATOR_RES`-style fold if a `"J2601-N"` (dash)
      variant of one of these ever shows up as a title-duplicate.
    - **SAE designations carry their revision/approval date as a
      trailing `_YYYYMM` suffix** on sae.org (e.g. `"J2601-5_202502"` =
      the edition of `J2601-5` current as of 2025-02) — not present in
      this corpus's own designations yet, but the same normalization
      question as follow-ups #10/#12 if it ever is.
    - **Concretely actionable, found while cross-checking this research
      against the corpus (not yet fixed, flagged for the user):**
      - `"SAE J2601"` and `"SAE J2601 /1"` share the exact same clean
        title ("Fueling Protocols for Light Duty Gaseous Hydrogen Surface
        Vehicles") — stronger evidence than a title-only match that
        `"/1"` really is spurious, matching the user's own suspicion.
      - A **third edition-date-suffix style**, not covered by follow-ups
        #10/#12: `"NAME: YYYY-MM"` (colon-space-year-dash-month), found
        on `"SAE J2600: 2015-10"` / `"SAE J2601: 2020-05"` — each has a
        same-title, bare-designation counterpart (`"SAE J2600"` /
        `"SAE J2601"`) with a stray `"J260N_YYYYMM "` prefix baked into
        *that* record's own title, which is why this pair didn't surface
        in the exact-title duplicate audit (follow-ups #10-#13) — it's a
        near-duplicate by title, not an exact one. **Fixed** (per the
        user's decision, 2026-09-11): `_COLON_YEAR_MONTH_SUFFIX_RE` added
        alongside the other two edition-date-suffix patterns in
        `deduplicate_db.py`/`analyze_similarities.py`. The `"/1"` question
        remains explicitly flagged, not touched.
      - **Re-run results**: 1 new regression test (191 total). Pipeline
        re-run: `"SAE J2600"`/`"SAE J2600: 2015-10"` and `"SAE
        J2601"`/`"SAE J2601: 2020-05"` each correctly merged into one
        record. Total record count stayed at **1194** rather than
        dropping to 1192 — coincidental, not a problem: the same
        pre-existing LLM-merge non-determinism already documented
        elsewhere in this plan (Step 1 follow-up #5) hit the `ISO 14687`
        cluster this particular run (it had auto-merged cleanly in
        follow-up #13's run, six records; this run gpt-4o-mini didn't
        collapse it as fully, eight records, four now correctly
        `flagged_for_review` instead of silently guessed) — the two
        effects offset. No bad merge either way; the review queue is
        doing exactly what it's for. `h2regdocs` reloaded (1217
        `Document` rows), `app/app.py` re-verified.
- **Follow-up #14 (2026-09-11): `TRBS 3151` / `TRGS 751` are confirmed
  the same document — a genuine schema question, not a dedup bug.** The
  user's own explanation (translated from German, verbatim below) settles
  what follow-up #11 had flagged as merely "possibly the same rule cited
  with varying completeness":

  > There is no substantive difference between TRBS 3151 and TRGS 751.
  > It is one and the same set of rules, published as a so-called
  > *Verbundregel* (a joint/combined rule with a dual designation).
  >
  > **Background on the dual designation**
  > - **Different legal domains**: TRBS (*Technische Regel für
  >   Betriebssicherheit* — Technical Rule for Operational Safety)
  >   specifies the requirements of the Ordinance on Industrial Safety
  >   and Health (BetrSichV). TRGS (*Technische Regel für Gefahrstoffe* —
  >   Technical Rule for Hazardous Substances) specifies the
  >   requirements of the Hazardous Substances Ordinance (GefStoffV).
  > - **Shared scope**: for filling stations and gas-filling
  >   installations, the topics of equipment/plant safety (equipment,
  >   pressure installations) and hazardous-substances law (handling of
  >   flammable liquids and gases) overlap heavily.
  > - **Joint development**: the rule set was jointly developed and
  >   adopted by the Committee for Operational Safety (ABS) and the
  >   Committee for Hazardous Substances (AGS), specifically to avoid
  >   contradictions between the two legal domains.
  >
  > In practice, it is therefore often simply referred to as
  > "TRBS 3151 / TRGS 751".

  **This is NOT a "same document, formatted differently" case like the
  rest of follow-ups #10-#13** — it's one document that is *officially,
  permanently* published under two designations at once (a genuine
  `Verbundregel`/joint-rule convention, not a citation inconsistency to
  normalize away). The Konsolidace schema's `Document.identifier` is a
  single `VARCHAR(100) UNIQUE` field — it has no place to record a second,
  equally-official designation for the same row. **Not resolved yet, per
  the user's own note ("I just do not know if we can handle it in our
  current schema")** — needs a real decision (e.g. a small
  `document_alias`/`alternate_identifier` table, or folding the second
  designation in as a searchable keyword) before this — or any future
  `Verbundregel`-shaped case — can be merged correctly rather than
  arbitrarily picking one designation and losing the other.
- **Future need, flagged by the user (2026-09-11), not scoped yet: a
  dedicated review/cross-check working mode for the database interface.**
  Several of the follow-up #10-#14 findings (the `CSA ANSI GSV/HGV`
  typo, the SAE `J2601`/`"/1"` question, the `TRBS`/`TRGS` dual
  designation) needed the user's own outside research to resolve
  confidently — this kind of situation will keep coming up. The user
  wants a dedicated mode of `app/app.py` (or a successor interface) built
  specifically for surfacing and resolving these ambiguous near-duplicate
  cases, rather than working through `doc/PLAN.md` prose each time. Not
  designed yet — a candidate for its own `/plan` session later.

### Full-text fetch completed to the whole corpus (2026-09-11)

Per the same user decision, ran `src/tools/fetch_fulltext.py` (previously
only smoke-tested with `--limit 5`) to completion against the full raw
corpus (not just `Sinay_Zakony` — `Haltuf_Dokumenty`'s 164 URL-bearing
law records had never actually been fetched).

- **Found and fixed a real bug on the first full run**: several Haltuf
  `odkaz_hlavni`/`odkaz_eu` cells hold **two URLs joined by an embedded
  newline** (an Excel line-break artifact — the real EUR-Lex PDF link
  followed by an unrelated informational page), so the whole blob was
  sent as one URL and 404'd. Added `first_url()` (splits on whitespace,
  keeps the first token) — fixed 10 of the initial 14 failures. 3 new
  tests.
- **Final result: 140/144 URLs fetched** (97%), 105 MB across
  `data/fulltext/{Haltuf_Dokumenty,Sinay_Zakony}/` (git-ignored, per §4).
  The 4 remaining failures are genuine, disclosed external limitations,
  not bugs: `ISO 16111` and `EN 50129` (403/404 — both are actually norm
  citations that slipped into `Haltuf_Dokumenty`, a reminder that this
  source's law/norm classification isn't 100% precise, though no
  paywalled content was captured since both failed), `ADR 2025` and
  `UNECE Regulation No. 100` (403 — UNECE blocks automated access).
- All fetched content is born-digital text-layer PDF/HTML (verified: EUR-Lex
  PDFs open as real multi-page documents, not scans) — no OCR needed,
  already in a form `fetch_fulltext.py`'s own consumers (or any future
  text-extraction step) can parse automatically. Extracting *clean* text
  out of that raw HTML/PDF (stripping site chrome, running a
  PDF-to-text pass) is a distinct, not-yet-built next step if needed —
  flagged, not assumed.

### Step 2 — Load into the real schema — DONE 2026-09-09

- **`src/tools/init_db.py` rewritten** to populate every Konsolidace-added
  column, not just the 7 pre-Konsolidace ones: `identifier` (← `znacka`),
  a new `Document.jurisdikce` column (see below), and one `DocumentVersion`
  row per `Document` (`version=1, is_current=TRUE` — no real version
  history exists in the JSON, so "first load is version 1, current" is the
  correct seed, not a simplification). Kept the existing TRUNCATE-and-reload
  architecture and `get_or_create` helper pattern; extracted the new
  mapping logic into small, pure, unit-tested functions
  (`resolve_identifier`, `resolve_document_type`, `normalize_jurisdikce`,
  `build_gestor_jurisdiction_map`, `resolve_source_jurisdiction`).
- **Schema correction, found and fixed while implementing this step:**
  `Konsolidace-DB-popis.md` §4.2 claimed "jurisdiction is a property of the
  source, not the document" (V03 §6.4) — **empirically false for this
  corpus**: 1276/1344 records (95%, nearly all norms) have a *blank*
  `gestor`, so they'd all collapse onto one shared `DocumentSource` row
  spanning 11 different `jurisdikce` values. Added a new, additive
  `Document.jurisdikce VARCHAR(20) NULL` column instead (applied directly
  to the live `h2regdocs` plus appended to `Konsolidace-DB-schema.sql` for
  future fresh installs) — this is now the authoritative per-document
  field. `DocumentSource.institution_type`/`.jurisdiction` are kept as a
  best-effort *supplement* only for the ~68 records with a real, non-blank
  `gestor` (verified: zero real gestor→jurisdikce conflicts exist there).
  `Konsolidace-DB-popis.md` corrected in place (§3, §4.1, §4.2, §8.3, §9)
  rather than left standing as documented-but-wrong.
- **`typ_dokumentu` numeric-code cleanup**: 44 records (all
  `Haltuf_Dokumenty`) carry leaked category-id junk (`"1"`, `"2"`, `"9"`,
  …) instead of a real type label. `resolve_document_type()` folds any
  blank/purely-numeric value to a fallback `"Nezařazeno"` `DocumentType`
  rather than creating junk rows — contained entirely in the loader, not
  fixed upstream in `build_unified_db.py` (deliberate scope choice).
- **`identifier` collision handling**: `Document.identifier` is
  `VARCHAR(100) UNIQUE NULL`. Verified against the actual 1344-record
  corpus: only 2 genuine duplicate `znacka` values exist (`ASTM F1624-12`
  CZ+US, `DIN EN 10216-2` DE+EU — both the already-disclosed Step 1
  follow-up #9 residual), plus one record whose `znacka` is a
  177-character multi-standard bundle (a Sinay PDF-parsing artifact) that
  exceeds the column's 100-char limit. `resolve_identifier()` leaves
  `identifier` NULL (with a printed warning) for a collision or an
  oversized value rather than crashing the load or silently truncating.
- **`src/tools/check_db.py` rewritten** from one hardcoded query into a
  reusable load-health report: row counts per table, identifier/jurisdikce
  coverage, `DocumentVersion` 1:1-with-`Document` parity check, and a
  `458/2000 Sb.` spot-check (the same anchor `tests/test_search.py` uses).
- **Tests**: new `tests/test_init_db.py` (21 tests, no real DB needed —
  same mocking-free pure-function style as `tests/test_deduplicate_db.py`'s
  `build_clusters`). 128 tests total, all passing.
- **Load results**: 1344 `Document` rows, 1344 `DocumentVersion` rows
  (1:1, all `is_current=TRUE`), 39 `DocumentSource`, 3 `DocumentType`
  (`Norma`/`Zákon`/`Nezařazeno`), 255 `Keyword`, 3262 `DocumentKeyword`.
  1337/1344 identifiers resolved, 1268/1344 `jurisdikce` resolved (the gap
  is `Sinay_Zakony`/`Haltuf_Dokumenty` records, which `build_unified_db.py`
  never assigns a per-record `jurisdikce` to — a pre-existing, disclosed
  gap from Step 1, not new). `app/app.py` re-verified via the Flask test
  client (`/`, search, and all three filter routes still return 200) —
  confirmed purely additive, nothing it already depended on changed.

### Step 3a — Populate process layer B + node_document from V02 — DONE 2026-09-10

Neither V02 nor V03 (the source documents `Konsolidace-DB-popis.md`/
`-schema.sql` cite throughout) existed anywhere in this repository —
confirmed by exploration before this step could even be scoped. The user
then uploaded both: `doc/NAHYC DP004 V02 - Popis procesů.docx` and
`doc/NAHYC DP004 V03 - Popis regulatorního a procesního rámce.docx`.

Full-document exploration found a sharp split: **V02 is highly
structured** (every U1–U7 section repeats the same 11 H3 subsections,
with real Word tables for subjects/branch-outputs) and maps almost 1:1
onto layer B — genuinely extractable by a parser. **V03 is layer D — the
compliance pathway** (`technology_type`, `project_criterion`,
`node_activation_rule`, `use_case_scenario`, `scenario_*`) — thin, mostly
prose, and V03's own text (§5.7/7.2/7.3, "metodický nesoulad") says
formalizing activation rules is still an **open, unresolved methodological
gap**, not something to script or guess. Per the user's explicit decision
(2026-09-10), layer D was scoped out of this step entirely — see **Step
3b** below.

- **`src/tools/parse_v02_processes.py`** (new): parses the docx (via
  `python-docx`, newly added to `.venv`) into
  `data/v02_processes_parsed.json`. Two real structural exceptions found
  and handled explicitly rather than forced into the generic pattern:
  **U2** doesn't use lettered "Větev X" branch headings like U4–U7 — it
  uses "Krok 1–4" headings, with the real A–D branching living as a table
  *inside* "Krok 2 — Větvení procesu"; **U5** has a "Průřezově — ATEX
  klasifikace" H4 that isn't a branch at all, it's a modifier applying
  across U5's real branches. Also handled: two different list-formatting
  conventions in the source (`List Paragraph`-styled bullets for
  U1–U3/problems everywhere, vs. plain `Normal` paragraphs for
  U4–U7's inputs/steps) — `extract_list_items()` prefers `List Paragraph`
  when present, else falls back to `Normal` paragraphs minus the
  colon-terminated intro sentence, verified against every node's actual
  content before relying on it.
- **`src/tools/load_process_layer.py`** (new): loads the parsed JSON into
  `node_description`, `node_branch`, `branch_step`, `node_input`,
  `node_output`, `subject`, `node_subject`, `node_problem`, and the
  layer-C `node_document` link table — reusing `init_db.py`'s
  `get_connection()`/`get_or_create()` pattern. Citation matching (for
  `node_document` and the 59-entry bibliography) never guesses: a
  citation matched by digit-core (Czech laws/decrees, EU regulations) or
  exact text-core (technical norm codes, carefully NOT collapsing e.g.
  `STN EN 17124` into `ČSN EN 17124` — verified with a direct regression
  test) links to the existing `Document`; bibliography entries with no
  citation pattern at all (internal NAHYC/HYTEP/EHTA/academic sources)
  get a new `Document` row (`DocumentType` `"Bibliografický pramen"`,
  plus a seed `DocumentVersion` row matching Step 2's own invariant);
  anything that looks like a citation but doesn't match an existing
  `Document` goes to `data/process_layer_review_queue.json` instead of
  being silently dropped or risking a duplicate row.
- **Real bug found and fixed while first running this against the live
  DB**: `node_branch.branch_code` is `VARCHAR(5)` — the cross-cutting
  "Průřezově" heading doesn't fit as its own code (only single-letter
  A/B/C/D codes were anticipated). Fixed by using a short marker code
  (`"X"`) with the full description kept in `branch_name`.
  **Second bug, found while verifying `DocumentVersion` parity**:
  `load_process_layer.py` must run *after* `init_db.py` and needs its
  own TRUNCATE-and-reload reset (`node_document` has `ON DELETE
  RESTRICT` on `Document` — re-running `init_db.py` alone would leave it
  pointing at deleted rows). Added `reset_layer_b_tables()`, documented
  the ordering dependency directly in the script.
- **Tests**: `tests/test_parse_v02_processes.py` (25 tests) and
  `tests/test_load_process_layer.py` (12 tests) — pure helper functions
  with synthetic fixtures, no real docx/DB access. 165 tests total.
- **Load results**: 7/7 nodes with a `node_description`, 22 branches
  (2 linear MAIN + U2's Krok-based A–D + 15 lettered across U4–U7 + U5's
  cross-cutting), 75 steps, 46 inputs, 21 outputs, 38 subjects/47
  subject-links, 37 problems, 23 `node_document` LEGAL_BASIS links, 23
  new bibliography `Document` rows (1344 → 1367 total). 26 items in the
  review queue — genuine gaps (laws/norms V02 cites that aren't yet in
  the 1344-record corpus, e.g. živnostenský zákon, REACH/CLP, ČSN 73
  0804) or a bibliography entry that mentions a norm without itself
  being one (e.g. an IROP funding-conditions document citing EN
  17124/17127) — a disclosed, narrow limitation of the "does this entry
  contain a citation pattern" heuristic, not a crash or a guess.
  `app/app.py` re-verified via the Flask test client (unaffected — layer
  B/C are new tables/rows, nothing `app.py` already queries changed).

### Step 3b — Populate process layer D (compliance pathway) — designed 2026-09-10, postponed

Layer D (`technology_type`, `project_criterion`, `node_activation_rule`,
`use_case_scenario`, `scenario_value_chain`, `scenario_technology`,
`scenario_node`, `scenario_document`) represents the **compliance
pathway** — matching a concrete project profile against formalized
activation criteria. (The schema itself is already in place from Step 0
— this step is about content, not DDL.)

**Status (2026-09-10): postponed at the user's explicit direction** —
the project's priority right now is the regulatory-document database
itself (exact-once representation + automatically-parseable full text
for downloadable documents), not the process/compliance layers. This
section records the completed research and the exact input needed, so
the step can resume later without re-deriving any of it.

**Research findings (two full re-reads of V03, plus a check of whether
the underlying laws it points to are usable in-repo):**
- **V03 has zero enumerated, structured content for any layer-D table.**
  It's conceptually rich (four-domain value chain, four classification
  lenses, bottom-up methodology) but every layer-D-shaped list already
  in this document (`ELEKTROLYZER_PEM`/`KAPACITA_ELEKTROLYZERU`-style
  codes, the "1.2 MW electrolyzer" worked example) turned out to be
  **the schema author's own illustrative invention, not sourced from
  V03** — confirmed by direct comparison against the actual document
  text.
- **`node_activation_rule` is worse than thin — V03 itself calls it
  unresolved**: §10.6 states *"Za jakých přesných podmínek se
  elektrolyzér klasifikuje jako 'výroba plynu' podléhající licenci...
  tato otázka je klíčová... a její výklad by měl být potvrzen
  autoritativním zdrojem."*
- The one real, verbatim, regulator-grade number found anywhere in this
  repo's material is the **20 million CZK bond (kauce)** for pohonné
  hmoty distributors (V02, U4 section, tied to `311/2006 Sb.` — itself
  not yet a `Document` row; flagged in Step 3a's review queue). Every
  other threshold V03 alludes to (vyhrazená technická zařízení
  pressure/capacity classes, ATEX zones, Seveso A/B tiers) points at laws
  that are either not yet `Document` rows (`192/2022 Sb.`) or are
  `Document` rows with **no fetched full text**
  (`406/2004`, `116/2016`, `224/2015`, `250/2021 Sb.` — none in
  `data/fulltext/`; only `100/2001 Sb.` is fetched, and it has no
  hydrogen-specific content).
- **`technology_type` and `use_case_scenario` ARE draftable** from V03's
  own prose (not extraction-ready, but real material to structure): PEM
  electrolyzer, pressure/cryogenic storage, cylinders/trailers/pipelines,
  fixed+mobile HRS, FCEV buses/trucks/trains (trains deprioritized by
  stakeholders), KVET; and 6 named topic areas (§4.2) plus one fully
  worked scenario (1 MW PEM electrolyzer, bus depot, industrial zone).

**When this resumes, input needed from the user (not extractable, not to
be guessed) — `project_criterion` and `node_activation_rule`**, in this
shape, e.g. as `data/v03_layer_d_draft.json`:

```json
{
  "technology_type": [
    {"code": "ELEKTROLYZER_PEM", "name": "...", "description": "..."}
  ],
  "use_case_scenario": [
    {"code": "...", "name": "...", "description": "...",
     "application_area_code": "MOBILITA|ENERGETIKA|PRUMYSL|PILOTNI",
     "integration_level_code": "SAMOSTATNA|INTEGROVANA|KOMPLEXNI|OSTROVNI"}
  ],
  "project_criterion": [
    {"code": "KAPACITA_ELEKTROLYZERU", "name": "Instalovaný výkon elektrolyzéru",
     "data_type": "NUMERIC|BOOLEAN|ENUM|TEXT", "unit": "MW", "description": "..."}
  ],
  "node_activation_rule": [
    {"node_id": "U4", "branch_id_code": "B", "criterion_code": "KAPACITA_ELEKTROLYZERU",
     "comparator": "EQ|NE|GT|GTE|LT|LTE|IN|IS_TRUE|IS_FALSE",
     "value": "...", "rule_group": 1, "description": "...",
     "basis_citation": "458/2000 Sb."}
  ]
}
```

`application_area_code`/`integration_level_code` resolve against the
already-seeded lookup tables (both 4 rows). `branch_id_code` is optional
(null = whole node) and resolves against `node_branch` (loaded in Step
3a). `basis_citation` is optional, matched against `Document.identifier`
the same way Step 3a's citations were (same review-queue fallback on a
miss). The planned build (once content exists): a hand-edited JSON
(nothing left to parse from a docx), loaded by a new
`src/tools/load_layer_d.py` reusing `load_process_layer.py`'s
`normalize_citation_core`/`build_document_lookup`/`match_citation`
rather than reimplementing citation matching a third time, `technology_type`
and `use_case_scenario` drafted by the assistant from V03's own wording
first (clearly marked draft/needs-review) — see the user's 2026-09-10
decision above for the two-track split.

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

Not decided yet — see §5.

### 3.5 Why `verification_evidence` isn't implemented as literally specified

The proposal's anti-hallucination mechanism assumes the Extraction Agent
receives full source-document text to quote from. **None of this repo's
scripts ever have that.** `deduplicate_db.py`, `enrich_eu_laws.py`,
`enrich_annotations.py`, and `process_laws.py` only ever operate on
structured spreadsheet metadata (titles, dates, keyword lists) supplied by
partners — there is no raw legislative text anywhere in `data/` to check a
quote against. Building genuine verbatim-quote verification needs the
Parser Agent plus real document fetching, which §5 defers along with the
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

## 4. Full-text acquisition (laws + norms) — NEW, requested 2026-09-09, not yet designed

**Why this is needed, and why it doesn't have to wait for §3's full agentic
build-out:** every merge/dedup/similarity decision this pipeline makes
today rests on nothing but a title, a short annotation (often absent —
1311/2230 raw records have none), and a handful of metadata fields. The
Step 1 follow-ups already flagged this as a real weakness ("cosine
similarity over bare titles is inherently weak for terse/technical titles
that share domain vocabulary" — noted, deferred, never implemented). Having
each law's actual full text (and whatever can legitimately be captured for
each norm) available would give embeddings, LLM extraction, and human
review all a far richer signal — this is the concrete mechanism to finally
fix that deferred weakness, not just a nice-to-have alongside it.

**Scope, as specified by the user:**
- **Laws** — full text, from EUR-Lex (EU law), e-Sbírka (Czech law), and
  "relevant Slovak sources" (i.e. Slov-Lex, the Slovak national law portal
  — not named anywhere in this repo today despite the project already
  having a whole Sinay/Slovak-legislation branch), plus "possibly other
  national sources" (unspecified so far; German material is tracked via
  `Sinay_Normy`'s roadmap data today, but never fetched as full text).
- **Norms** (ČSN/STN/EN/ISO/DIN/...) — explicitly **not** open access, a
  fundamentally different legal situation from laws. Confirmed directly
  this session (Step 1 follow-up #7): the ČSN online registry's own Terms
  of Use state the documents are copyrighted by ÚNMZ/CEN/CENELEC/ISO/IEC
  and explicitly forbid bulk or software-automated downloading. **This
  pipeline must never attempt to scrape or download the actual protected
  standard text.** What's asked for instead is best-effort capture of
  whatever is *legitimately* publicly available per norm — an abstract or
  scope statement, table of contents, a publisher's own free preview/
  citation page — strictly bounded at what's freely published, never the
  paywalled document itself.

**Relationship to existing plan sections:**
- This concretizes §3.3 item 1 ("Source screening... Query EUR-Lex/e-Sbírka/
  ČAS APIs directly") — that bullet already implied documents get fetched
  (§3.2's Parser Agent row exists specifically to parse "raw PDFs/scans"
  source screening "will return"), but never named Slovak sources, "other
  national sources," or the laws-vs-norms legal distinction at all.
- The Parser Agent (§3.2) is the natural next stage after fetching — clean
  text out of a raw PDF/HTML page — but per §5 decision 1 (harden-existing-
  scripts-only scope), that agent and the rest of the LangGraph build-out
  were explicitly deferred. Full-text acquisition for *laws* doesn't need
  to wait on that: EUR-Lex/e-Sbírka/Slov-Lex already publish current
  legislation in machine-readable HTML/XML, not scanned PDFs needing VLM
  layout parsing — a plain fetch-and-store script (same style as
  `check_csn_validity.py`) is realistic well before the agentic system.

**Designed and implemented 2026-09-09** (via a dedicated `/plan` session,
as flagged above). Decisions taken: storage in a new git-ignored
`data/fulltext/` (not a MariaDB column — Step 2 hasn't happened yet, so
there's nowhere in the DB to put it), scoped to laws only (norms stay
paywalled/never fetched, unchanged), plus active source screening for
records without a URL or for documents not yet in the corpus at all —
querying real APIs, not guessing.

- **`src/tools/fetch_fulltext.py`**: fetches `odkaz_hlavni`/`odkaz_eu`/
  `odkaz_sk` for every `Haltuf_Dokumenty`/`Sinay_Zakony` record that has
  one (almost all of them — direct `eur-lex.europa.eu` PDF/HTML links for
  Haltuf, `zakonyprolidi.cz`/`slov-lex.sk` per-document pages for Sinay),
  into `data/fulltext/<zdroj_dat>/`. `Prokop_Normy`/`Sinay_Normy` are
  skipped unconditionally and visibly — this script must never be
  extended to fetch norm text. `data/fulltext_manifest.json` (small,
  git-tracked, no document content) makes reruns idempotent and is what a
  future Step 2 loader can use to populate `Document.file_path` without
  re-fetching anything.
- **Source screening — real APIs found and verified working while
  building this, not assumed from documentation alone:**
  - **`src/tools/screen_eurlex.py`**: the EUR-Lex Cellar SPARQL endpoint
    (`publications.europa.eu/webapi/rdf/sparql`) is public and
    unauthenticated — confirmed with a live `bif:contains` full-text
    query over `cdm:expression_title`. Diffs matched CELEX ids (via a
    year/number extraction, e.g. `32014R0559` → `2014/559`) against the
    corpus's own znacka values and reports only genuinely new ones.
  - **`src/tools/screen_esbirka.py`**: e-Sbírka's actual public REST API
    (`sbr-externi`, per its own frontend config) turned out to require
    Ministry-of-Interior client registration — not something this script
    can obtain — and doesn't resolve anonymously anyway (dead-ends at an
    internal port). Found a separate, real, public, unauthenticated
    Linked Open Data SPARQL endpoint instead
    (`opendata.eselpoint.gov.cz/sparql`, covering the same content,
    individual acts addressable by ELI). **Disclosed limitation**: a
    full-text hit there doesn't reliably back-link to its owning act's
    citation in a scrapeable way (unlike EUR-Lex's CELEX-in-the-triple
    convenience) — every hit is reported as an *unresolved* candidate for
    human triage rather than guessing which law it belongs to.
  - **`src/tools/screen_slovlex.py`**: Slov-Lex has no confirmed public
    API or full-text search (only a paid third-party service) and its
    search UI is a JS-only SPA — genuinely not screenable for new
    documents right now. Scoped down, honestly, to what actually is
    achievable: checking that the `odkaz_sk` links already in the corpus
    still resolve (confirmed useful — `slov-lex.sk` is known to
    restructure its URLs; a direct link 301s twice before landing today).
  - All three write to a single, git-tracked review file,
    `data/fulltext_screening_candidates.json` (one key per source) —
    never an auto-write into `database_merged_raw.json`, same principle
    as `data/dedup_review_queue.json`.
- **Tests**: `tests/test_fetch_fulltext.py`,
  `tests/test_screen_eurlex.py`/`_esbirka.py`/`_slovlex.py` — pure diffing/
  parsing logic plus HTTP layers mocked, no real network calls in the
  suite itself; 43 new tests (110 total, all passing).
- **Not done in this pass** (see the plan file's "explicitly out of
  scope" section): wiring fetched text into embeddings/dedup similarity
  or into MariaDB — Step 2 still hasn't happened, this only builds
  acquisition + storage + manifest. Consuming it is a later, separate
  step, same as the deferred "embed title+annotation" idea above.

## 5. Open decisions

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
