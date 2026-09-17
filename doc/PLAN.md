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
itself: Step 1 follow-ups #10–#19 (2026-09-11) found and fixed real
missed-duplicate/parsing/classification bugs via a systematic
duplicate-title audit (1344→1200→1196→1194→1191→1188→1176→1189→1191→1186→1188
records; of the #17 step's +13, 12 are genuinely new content — see
follow-up #17 — and 1 is the usual LLM-merge non-determinism noise
documented elsewhere in this plan, not a new issue); only 1
of the original 2 known cross-jurisdiction `identifier` collisions
remains — the other turned out to be a classification bug, not a genuine
cross-jurisdiction duplicate). `CSA ANSI GSV 4.1`→`HGV 4.1` (typo),
`ISO 7105`→`STN 65 1312-2` (withdrawn) and `EIGA 121/14`/`IGC Doc 121/14`
(org-rename alias) resolved, each a one-time data correction and/or
narrow normalization fix; `SAE J2601 /1` remains flagged, not acted on.
Follow-up #14 confirmed `TRBS 3151`/`TRGS 751` as one document published
under two official designations (a German *Verbundregel*) — a genuine
schema gap (no place for a second identifier), not resolved yet.
Follow-up #15 generalized a jurisdikce bug found via the `ISO 7105`/`ISO
14313` cases: a bare international ISO/IEC designation was being marked
CZ/SK in three places, purely because of its source column/file — now
fixed, with a beneficial ripple effect on several other cross-source
merges. Follow-up #16 fixed the same kind of bug for bare "EN ISO"
designations (→`EU`, not `mezinárodní`), fixed a real parsing bug
(`STN EN 1514` collapsing 7 standards into one unusable record), and
designed + implemented a real version-history data model: norm
base+amendment pairs now populate multiple `DocumentVersion` rows on one
`Document` (17 groups linked), while a law amended by a separately-
numbered act uses a new `document_relation` table instead (1 real
example loaded: `426/2021 Sb.` AMENDS `266/1994 Sb.`). Follow-up #18
resolved the two real duplicates found in the deferred "draft-stage"
bucket (`ISO 11954`/`ISO/TR 11954`, `IEC 62933-5-1`/`IEC/TS 62933-5-1` —
the latter's title traced to a copy/fill-down error in the raw XLSX),
confirmed the other 18 pairs are correctly separate (published + an
in-development revision); `TNI`/`STN CLC/TR 60079-32-1` marked withdrawn
per the user's own research (real current document is Czech, `ČSN
CLC/TR 60079-32-1`); and extended `link_document_versions.py` with an
EN-IEC-renumbering fold so `STN EN 60079-11/-14/-17` (a third pair,
`-14`, found once the mechanism was generalized) now version-link
correctly too, on top of the 17 amendment pairs (20 total). Follow-up
#19 re-audited both buckets once more (nothing missed), fixed a real
title bug in `DIN 50450-2`/`-9` (same copy/fill-down shape as `IEC
62933-5-1`), and gave every orphaned amendment a durable, queryable
flag (`data/orphan_amendment_review_queue.json`, 10 entries) instead of
leaving them only noted in this plan. A dedicated
review/cross-check working mode for the database interface is a flagged
future need, not designed yet. The agentic
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
  - **`CSA ANSI GSV 4.1` vs. `CSA ANSI HGV 4.1` — re-examined 2026-09-11,
    resolved with a one-time manual data correction (not a code/
    normalization rule).** Re-reading both full records (not just the
    earlier CSA-store check) showed identical title ("Hydrogen-dispensing
    systems"), identical `platnost` (2020-03), and a byte-identical
    `anotace_poznamka` — with GSV's single keyword
    (`Sicherheitstechnische Grundsätze`) a subset of HGV's four. Combined
    with the earlier finding that no `"GSV"` standard exists in the CSA
    store (only `CSA/ANSI LNG 4.1`, `CSA/ANSI NGV 4.1`) and every other
    entry in this corpus's `CSA ANSI HGV *` series (2, 3.1, 4.1, 4.10,
    4.2, 4.3, 4.4, 4.8, 4.9) is spelled "HGV" — this is the same
    document duplicated under a single-letter typo, not a real second
    standard. Tracing the typo to its origin found it independently in
    **both** raw Sinay_Normy sources: (1) the XLSX
    `data/20250712_Sinay/raw/Zoznam_noriem_Vodik_Road_map_Nemecko_
    Priradenie_STN_VERZIA_2024_06_27b.xlsx`, sheet "NRM
    H2_Bestandsanalyse", cell `B88` — corrected in place (GSV → HGV;
    note the resave via `openpyxl` drops an unsupported Data Validation
    extension the file carried, per its own load warning — cosmetic,
    doesn't affect any value read by `parse_sinay_norms.py`); and (2) the
    PDF `data/20250712_Sinay/raw/Zoznam_noriem_vodik-11_02_2025.pdf`,
    page 41 — not hand-editable the way an XLSX cell is, so instead
    corrected directly in the generated intermediate
    `data/20250712_Sinay/sinay_normy_processed.json` (record index 594,
    `Značka`). **This JSON-level patch is NOT durable**: a future re-run
    of `parse_sinay_norms.py` regenerates this file from the raw PDF/XLSX
    from scratch, and since the XLSX source is now fixed but the PDF
    source still literally reads "GSV" on page 41, the same single
    record (the PDF-derived one) would need this exact one-line manual
    patch reapplied by hand — deliberately not automated, per the
    decision below. **Decision (user, 2026-09-11): fix the data, not the
    code** — a generalized normalization rule would be unwarranted for an
    isolated data-entry slip; revisit only if the official CSA repository/
    store itself is found to carry the same "GSV" typo. Full pipeline
    re-run after the fix: `database_merged_deduplicated.json` dropped
    from 1194→1191 records — 1 from this merge, the other 2 from the
    pre-existing, already-documented `ISO 14687` LLM merge
    non-determinism (follow-up #5), not a new issue (confirmed by direct
    before/after diff). 191 tests still pass, `h2regdocs` reloaded (1214
    `Document` rows, same historical +23 offset over the JSON count
    documented previously), Flask smoke test confirms a single
    "Hydrogen-dispensing systems" / `CSA ANSI HGV 4.1` record with all
    four keywords merged, no remaining "GSV" anywhere in the corpus. Also
    still note (unchanged from before): the corpus consistently omits the
    "/" CSA itself uses in its own branding (`"CSA/ANSI"`, not `"CSA
    ANSI"` — already handled for matching purposes by follow-up #11's
    separator fold, but stored designations remain un-rewritten,
    matching this pipeline's general practice). **Still separately
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
      - **Decision (user, 2026-09-11): standard-numbering questions like
        this are left for manual resolution as they come up, not
        automated.** Discussed building a lightweight "orphan part
        number" flagger (e.g. a family with `/2 /3 /4 /5` present but
        `/1` not fitting the pattern → review queue) using only signals
        already in the corpus, no external scraping — but validating
        whether a specific part number is genuinely real still needs
        authoritative per-family knowledge (sae.org, iso.org, ...) that
        the corpus alone can't provide and that changes over time, same
        reason this project never built a CSA/SAE catalog scraper. Not
        scoped as a task; `"SAE J2601 /1"` and any future case like it
        get resolved one at a time, by hand, the same way this one was
        researched.
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

- **Follow-up #15 (2026-09-11): acted on the two remaining "other"
  duplicate-title findings and fixed the systemic root cause behind
  both — a bare international ISO/IEC designation was being marked with
  a national jurisdikce (CZ/SK) in three separate places, purely because
  of which source column/file it came from, not because of anything in
  the designation itself.**
  - **`ISO 7105` (SK) — marked withdrawn, restored to its real
    designation, per the user's decision.** Its own source note (already
    quoted in follow-up #12's write-up) says the actual Slovak adoption
    was `STN 65 1312-2/ – 1990.09`, cancelled 2006-11-01 without
    replacement — the record had been carrying the bare international
    number (`"ISO 7105/ - 1985.06"`) instead. One-time manual data
    correction (same PDF-sourced-record limitation as follow-up #14's
    `CSA GSV` fix — patched directly in the generated
    `sinay_normy_processed.json`, needs reapplying if the PDF is ever
    re-parsed from scratch): `znacka` → `"STN 65 1312-2/ – 1990.09"`,
    `Kategorie` → `"STN (zrušená bez náhrady)"`, `Platnost` →
    `"zrušená 01.11.2006 bez náhrady (pôvodne prijatá 09/1990 na základe
    ISO 7105:1985)"`, the historical note moved into `Anotace`. Now
    correctly jurisdikce `SK` (via its own real `STN` prefix, not the
    bare-ISO override below) and no longer collides with the live
    international `ISO 7105` record.
  - **`EIGA 121/14` merged with `IGC Doc 121/14`.** EIGA's former name
    was IGC (International Gases Committee) — this is the *same* 2014
    edition under the old vs. new org name. Added a narrow prefix fold,
    `_EIGA_IGC_PREFIX_RE` (`deduplicate_db.py`, mirrored in
    `analyze_similarities.py`'s `core_znacka()`), stripping only the
    `"EIGA Doc "`/`"EIGA "`/`"IGC Doc "` prefix — deliberately not the
    edition/number suffix, so `"EIGA Doc 6/19/E"` (2019) vs. `"IGC Doc
    6/02/E"` (2002), a genuinely different edition of the same code, not
    just a renamed org, correctly stays unmerged (regression test
    included). A third citation style found while checking this,
    `"EIGA IGC Doc 121/14 (2014)"`, wasn't folded by this narrow rule
    (different token order) and remains a separate record — noted, not
    chased further this pass, out of the scope actually asked for.
  - **Root cause, generalized: "pure ISO is not marked
    Czech/Slovak/German", per the user's explicit instruction.** Tracing
    why `ISO 7105` and `ISO 14313` (also flagged in follow-up #12) ended
    up `SK` at all found the same shape of bug in **three** places, all
    now fixed:
    1. `classify_jurisdikce()` (`parse_sinay_norms.py`) could be tripped
       by an unrelated `STN` substring inside free-text `Kategorie`/note
       prose (the `ISO 7105` case: its note literally reads "...bola do
       sústavy STN prijatá..."). Added `_BARE_ISO_IEC_DESIGNATION_RE`
       (`^(?:ISO|IEC)(?:/[A-Z]+)?\s+\d`), checked FIRST, before any
       marker — a bare ISO/IEC designation is the international standard
       by definition, regardless of surrounding text.
    2. `parse_xlsx()`'s STN-column override (`"SK" if stn_designation
       else classify_jurisdikce(...)"`) blindly trusted the column being
       populated — but the `ISO 14313` case shows the column itself can
       just hold the bare international number, with no distinguishing
       national number ever assigned. Now skips the override (falls
       through to `classify_jurisdikce()`, which returns `mezinárodní`)
       when the STN-column value itself is a bare ISO/IEC designation.
    3. `build_unified_db.py`'s Prokop branch hardcoded `jurisdikce: "CZ"`
       for every record on the (until now correct-looking) assumption
       that Prokop is exclusively a ČSN catalog — but 5 real records
       (`ISO 22734:2019`, `ISO 11114-2`, `ISO 11114-4`, `ISO 6892-3`,
       `ISO 19880-9`) are bare international citations, not ČSN
       adoptions. New `resolve_prokop_jurisdikce()` applies the same
       bare-ISO/IEC check (duplicated regex, matching this codebase's
       existing convention of independent per-file copies rather than
       cross-importing between these scripts).
  - **Beneficial ripple effect, not separately chased**: removing the
    false `CZ`/`SK` jurisdikce also un-blocked several previously-stuck
    cross-source merges that the jurisdikce veto had been (correctly, at
    the time) keeping apart only because of the bug — `ISO 22734:2019`
    (Prokop) with `ISO 22734` (Sinay), `ISO 19880-1`, `ISO 19880-9`,
    `ISO 11114-1`, and a reshuffle of the `ISO 14687` cluster so records
    that are genuinely just the international standard (previously
    swept into the `ČSN ISO 14687` cluster only because Prokop's copy
    was mislabeled `CZ`) now correctly land in the international
    record, leaving a cleaner, smaller `ČSN EN ISO 14687` cluster for
    the real ČSN adoption. `dedup_review_queue.json` empty (no new
    ambiguous clusters).
  - **Re-run results**: full pipeline re-run
    (`parse_sinay_norms.py` → `build_unified_db.py` → `deduplicate_db.py`
    → `init_db.py` → `load_process_layer.py`). Deduplicated **1191→1188
    records**. 7 new regression tests (198 total). `h2regdocs` reloaded
    (1211 `Document` rows, same +23 bibliography offset as before),
    `app/app.py` re-verified (single merged `EIGA 121/14` record, `ISO
    7105` search surfaces the corrected `STN 65 1312-2` record).
- **Follow-up #16 (2026-09-11): three requests — a further jurisdikce
  fix (bare "EN ISO"/"EN IEC" → `EU`), a parsing bug found while
  auditing the deferred "amendment pairs" (`STN EN 1514`, one row =
  7 real standards crammed into one), and a proper version-history data
  model for norm base+amendment pairs, checked against the law-amendment
  case too.**
  - **Bare "EN ISO"/"EN IEC" (no national prefix) is `EU`, not
    `mezinárodní`.** A European (CEN/CENELEC) adoption of an ISO/IEC
    standard is one rung below a national adoption (e.g. `"STN EN ISO
    14687"`) and NOT the same thing as a bare `"ISO 14687"` citation
    (no European ratification at all) — but the marker loop's own
    generic `\bISO\b`/`\bIEC\b` rule was matching first and collapsing
    both into `"mezinárodní"`. Real cases found: `"prEN ISO 22734-1"`,
    `"prEN ISO 24078"`, `"prEN ISO 24490"` (all Sinay_Normy). Fixed with
    a new `_BARE_EN_ISO_DESIGNATION_RE`, checked right after the
    existing bare-ISO/IEC check (both in `classify_jurisdikce()` and the
    `parse_xlsx()` STN-column override), and mirrored in
    `build_unified_db.py`'s `resolve_prokop_jurisdikce()` (no triggering
    Prokop record currently, added defensively for consistency). 6 new
    tests.
  - **A real bug found while re-examining the amendment pairs: `"STN EN
    1514"` collapsed 7 real standards into one unusable record.** One
    row in the raw XLSX (`Zoznam_noriem_Vodik_Road_map...b.xlsx`, row
    266) holds a single cell listing all 7 parts of the `EN 1514` family
    (`-1`, `-2+A1`, `-3`, `-4`, `-6`, `-7`, `-8`), each with its own
    edition date, joined by embedded newlines — same shape for the title
    cell. The parser took the whole blob as one 190+ character `znacka`,
    already silently dropped by `init_db.py`'s identifier-length guard
    (a pre-existing, previously-unexplained WARNING in every pipeline
    run's output). Confirmed a genuine one-off in the raw source (only
    this one row has this shape, checked corpus-wide) — not a systemic
    pattern needing a general rule. Fixed with
    `split_multi_part_designation_row()` in `parse_sinay_norms.py`:
    pairs the designation cell's lines with the title cell's lines
    positionally (tolerating one shared preamble line before the
    per-part title lines), emitting N separate records instead of one;
    returns `None` (falls back to the historical single-record
    behavior) for any shape it doesn't confidently recognize, rather
    than guessing. 4 new unit tests plus an end-to-end `parse_xlsx()`
    test. Re-run: XLSX now extracts 975 records (was 969, +6 net for the
    7-way split of this one row), all 7 `STN EN 1514-*` parts now
    correctly present and separately citable (alongside the pre-existing
    `"STN EN 1514 (súbor)"` family-level catalog entry, which is a real,
    distinct STN catalog concept — bundled purchase of the whole family —
    not a duplicate of the 7 individual parts).
  - **Version-history data model, designed for norms and checked
    against the law-amendment case.** The two cases are NOT the same
    shape, confirmed by checking the corpus for a real law-amendment
    example (found: `"426/2021 Sb."`, titled "novela Zákona o drahách",
    amends `"266/1994 Sb."` — two separate, permanently distinct Document
    rows, each with its own real citation number):
    - **A norm's amendment (`+A1`/`/A1`/`/AC`) IS the same document, a
      later edition of the same designation** — this is exactly what the
      already-existing `DocumentVersion` table (with `is_current`,
      added at V03) is for, and it was never actually being used that
      way: every record got exactly one `DocumentVersion` row, so a
      base/amendment pair was two unrelated-looking `Document` rows that
      merely happened to share a title.
    - **A law amended by a separately-numbered act is NOT a new version
      of the same document** — both remain their own citable `Document`
      rows forever; the relationship between them is a different kind of
      fact entirely, modeled with a new table, not `DocumentVersion`.
      (If the corpus ever gains "úplné znění" — a consolidated republished
      text under the SAME law number after folding in amendments — THAT
      case would map to `DocumentVersion`, same as a norm's amendment;
      not implemented now, no such record currently in the corpus.)
    - **Schema (`doc/konsolidace/Konsolidace-DB-schema.sql`, applied to
      live `h2regdocs`)**: `ALTER TABLE DocumentVersion ADD COLUMN
      edition_label VARCHAR(200), ADD COLUMN effective_date VARCHAR(200)`
      — `version` alone is an opaque ordinal; `edition_label` carries the
      actual, verbatim, citable designation string for that edition,
      `effective_date` its own free-text validity note (same convention
      as `Document.effective_date`). New `document_relation` table
      (`from_document_id`, `to_document_id`, `relation_type` — `AMENDS` /
      `REPEALS` / `IMPLEMENTS` / `CONSOLIDATES`, `note`) for the law
      case. Full description in `Konsolidace-DB-popis.md` §4.3/§4.4.
    - **`src/tools/link_document_versions.py`** (new): groups records by
      an amendment-marker-and-edition-date-stripped designation core
      (`version_group_key()` — deliberately more tolerant than
      `deduplicate_db.normalize_znacka()`, since stripping an embedded
      `/A1` can remove the very `/` that suffix-stripping needs) plus
      jurisdikce, requiring at least one member to carry a real
      amendment marker (never sweeps in a coincidental title/core match
      with no amendment evidence — that's `deduplicate_db.py`'s job).
      Orders by `amendment_level()` (0 = base, 1 = `+A1`/`/AC`, 2 =
      `+A2`, …) — deliberately NOT by the free-text `platnost`/edition
      date, which this corpus does not reliably carry as the specific
      edition's own real date (found while checking: one base record's
      `platnost` carries an unrelated internal work-item-tracking date,
      `"2023-05"`, instead of its own real 2015 publication date).
      Merges each group into one record: the highest-amendment-level
      member's own fields become the current/top-level fields, keywords
      and sources are unioned, and a `versions` list records every
      member's own designation/date/current-flag. Run AFTER
      `deduplicate_db.py`, BEFORE `init_db.py`; rewrites
      `database_merged_deduplicated.json` in place. 16 new tests.
    - **`init_db.py`**: `resolve_document_versions()` replaces the old
      hardcoded single-row insert — a record without a `"versions"` list
      (the common, unversioned case) keeps the exact historical
      behavior (`version=1, is_current=TRUE`, no label/date); one WITH a
      list gets one `DocumentVersion` row per entry, numbered in order,
      each with its own `edition_label`/`effective_date`/`is_current`. 3
      new tests. `check_db.py`'s health report updated to treat >1
      version per document as expected/reported, not an error (the old
      "expect == doc_count"/"expect 0" wording assumed every document
      had exactly one version, no longer true).
    - **`src/tools/load_document_relations.py`** (new, small): loads
      `data/document_relations.json` — a short, HAND-curated list (like
      `data/v03_layer_d_draft.json`; detecting this reliably across the
      whole corpus needs human judgement, since an amending act's title
      typically names the amended law by subject, not by citation
      number) — into `document_relation`, matching by `Document.identifier`.
      Unmatched identifiers/relation types go to
      `data/document_relations_review_queue.json`, never guessed.
      Currently populated with the one real, confirmed example:
      `"426/2021 Sb." AMENDS "266/1994 Sb."`. 4 new tests.
  - **Re-run results**: full pipeline re-run (`parse_sinay_norms.py` →
    `build_unified_db.py` → `deduplicate_db.py` →
    `link_document_versions.py` → `init_db.py` →
    `load_document_relations.py` → `load_process_layer.py`).
    Deduplicated 1188→1193 (net +5 from the EN 1514 split, after the
    usual small LLM-merge-non-determinism noise) →
    **1176 after version-linking** (17 base+amendment groups found and
    merged — matches the count from the earlier "amendment pairs" audit,
    plus 2 more surfaced by this script's designation-core grouping,
    which is stronger evidence than the earlier exact-title check: `STN
    EN 746-1` and `STN EN 88-2`, the latter verified by hand — its
    "different" title is the same standard retitled with its pressure
    range restated in kPa instead of mbar/bar, 500 mbar–5 bar = 50–500
    kPa). `h2regdocs` reloaded: 1199 `Document` rows (1176 + 23
    bibliography), 1216 `DocumentVersion` rows (1199 + 17 real second
    editions), exactly 1199 with `is_current=TRUE`, 1
    `document_relation` row loaded cleanly. 230 tests total, all
    passing. `app/app.py` re-verified.
  - **Not done this pass**: no attempt to mine the corpus for more
    law-amendment relationships beyond the one confirmed example — needs
    human judgement per case, not a pattern to automate (see
    `load_document_relations.py`'s own docstring).
- **Follow-up #17 (2026-09-11): reviewed the remaining 26
  `process_layer_review_queue.json` items (13 unique citations, node-
  level + bibliography) and added the 12 that turned out to be genuine
  content gaps, not a matching bug.** Cross-checked every citation
  against the full corpus directly: 12 laws/regulations/norms cited by
  V02 (nodes U2/U4/U5/U6/U7 and its own bibliography) were simply never
  in the corpus at all — `114/1992 Sb.` (ochrana přírody a krajiny),
  `541/2020 Sb.` (odpady), `311/2006 Sb.` (pohonné hmoty — the same law
  already flagged back in the postponed Step 3b research as the source
  of the 20 mil. Kč distributor bond), `455/1991 Sb.` (živnostenský
  zákon), `192/2022 Sb.` (NV o vyhrazených tlakových zařízeních),
  `246/2001 Sb.` (vyhláška o požární prevenci), `13/1997 Sb.` (pozemní
  komunikace), `274/2001 Sb.` (vodovody a kanalizace), `268/2009 Sb.`
  (vyhláška o technických požadavcích na stavby), `(ES) 1907/2006`
  (REACH), `(ES) 1272/2008` (CLP), `ČSN 73 0804` (požární bezpečnost
  staveb — výrobní objekty). The 13th, `"EN ISO 17268"`, is a correctly-
  flagged ambiguity, NOT a gap and NOT touched: the corpus already has
  `ČSN EN ISO 17268` and `STN EN ISO 17268` (national adoptions), but
  citation matching deliberately never guesses which jurisdiction's
  adoption a bare, prefix-less citation means (same philosophy as
  `core_znacka()`'s ČSN-prefix stripping being scoped to clustering only,
  never to this exact-match citation lookup).
  - **New source, `data/v02_bibliography_documents.json`**: a small,
    hand-curated list of the 12 documents above, in final record shape
    (titles/identifiers verbatim from the V02 bibliography text; ministry
    `gestor` assignments are well-established general knowledge for these
    statutes; `platnost` left blank rather than guessed at the exact
    effective date, matching this project's established practice).
    Wired into `build_unified_db.py` as a 5th source
    (`"V02_Bibliografie"`) — appended as-is, no parsing needed since
    there's no raw spreadsheet behind it.
  - **Re-run results**: full pipeline re-run (`build_unified_db.py` →
    `deduplicate_db.py` → `link_document_versions.py` → `init_db.py` →
    `load_document_relations.py` → `load_process_layer.py`). All 12 new
    records survived deduplication untouched (no false merges),
    `dedup_review_queue.json` empty. `process_layer_review_queue.json`
    dropped from 26 to exactly 2 (only the `EN ISO 17268` node +
    bibliography entries remain, as expected). `h2regdocs` reloaded:
    1212 `Document` rows (+12), `node_document` (LEGAL_BASIS) grew for
    every citing node (U2 4→6, U4 2→5, U5 8→11, U6 2→4, U7 5→7 — 12 new
    links total, `311/2006 Sb.` correctly linked from both U4 and U7,
    spot-checked directly via SQL), 3 new `DocumentType` rows (`Nařízení
    vlády`, `Vyhláška`, `Nařízení EU`). 230 tests still pass (no new
    pure function needed — this was a mechanical, structurally-identical
    5th loading block, same as the existing 4). `app/app.py` re-verified.
- **Follow-up #18 (2026-09-11): reviewed the deferred "draft-stage" (21
  groups) and "ambiguous renaming" duplicate-title buckets.** Checked
  every pair's `platnost`/`kategorie_trida` (draft/work-item status
  text) and, for the renaming cases, `anotace_poznamka`.
  - **18 of the 21 draft-stage pairs confirmed correctly separate, not
    duplicates — no action.** One member explicitly shows draft/work-
    item status (`"v príprave"`, `"Arbeitsdokument"`, `"Entwurf-Návrh"`)
    alongside the other's real published edition — a published standard
    plus a currently-in-development revision/upgrade project, genuinely
    different lifecycle states already correctly documented by the
    existing status text.
  - **2 confirmed real duplicates by the user's own research, fixed as
    one-time source corrections** (same PDF/XLSX-sourced-record
    limitation as follow-ups #14/#15 — patched in the generated
    `sinay_normy_processed.json`, needs reapplying if those sources are
    ever re-parsed from scratch):
    - **`ISO 11954`/`ISO/TR 11954`**: per the user, only `ISO/TR
      11954:2008` and `ISO/TR 11954:2024` exist — no bare "ISO 11954"
      full standard. Both PDF- and XLSX-sourced occurrences of the bare
      form (missing `/TR`) corrected to include it. The two real
      editions (2008, 2024) must stay separate records — but giving them
      distinct `/ - YYYY.MM` suffixes still collided them, because
      `normalize_znacka()`'s edition-date-suffix strip deliberately
      ignores what the actual date is (that's what makes `"ISO 16111"`
      and `"ISO 16111/ - 2018.08"` correctly merge as the same
      standard) — the 2008 edition needed a **parenthetical** year,
      `"ISO/TR 11954 (2008)"`, not matched by any of the three known
      suffix regexes, to stay distinct from `"ISO/TR 11954/ - 2024.01"`.
      Kategorie on the 2008 record now notes it's superseded.
    - **`IEC 62933-5-1`/`IEC/TS 62933-5-1`**: confirmed via
      `https://webstore.iec.ch/en/publication/72239` that both records'
      title ("Road vehicles - Compressed gaseous hydrogen...") is simply
      wrong — the real IEC 62933-5-1:2024 is "Electrical energy storage
      (EES) systems - Part 5-1: Safety considerations for grid-integrated
      EES systems", replacing `IEC TS 62933-5-1:2017`. Root-caused
      directly in the raw XLSX (`Zoznam_noriem_Vodik_Road_map...b.xlsx`,
      rows 635/636/647): the German/English title columns for these
      *three* rows were contaminated with an unrelated CGH2-fuel-system
      title (a copy/fill-down error in the source spreadsheet) — row
      636 (`IEC 62933-5-2`) escaped the bug in its own OUTPUT record only
      because its Slovak title column (which the parser prefers) was
      separately, correctly filled in; rows 635/647 had no such
      fallback. Corrected both titles to the real IEC-verified text; the
      corpus's own already-correct `STN EN IEC 62933-5-1/62933-5-2`
      records (from the PDF source, unaffected by this XLSX bug)
      confirm the real Slovak-adopted content was never wrong. The
      `IEC/TS` (2017, superseded) record's `kategorie_trida`/`platnost`
      now say so explicitly.
    - **Flagged by the user, not yet acted on**: "there might be other
      IEC 62933 components ignored by the previous data collection
      step" — plausible given the confirmed row-636-area corruption, but
      determining which additional IEC 62933 parts are actually relevant
      to a hydrogen-focused corpus (most of the series covers general
      grid battery storage, not hydrogen specifically) needs a scoping
      decision, not just a lookup. Not investigated further this pass.
  - **The 3 "ambiguous renaming" cases, re-examined with the user's
    research:**
    - **`STN EN 60079-11`(2012)/`STN EN IEC 60079-11`(2025) and `STN EN
      60079-17`(2014)/`STN EN IEC 60079-17`(2024): confirmed real
      version pairs** (byte-identical annotations in both pairs; IEC's
      real 2016+ renumbering of the whole 60079 series, `EN 60079-N` →
      `EN IEC 60079-N`, plus a genuine edition update years apart) —
      **now version-linked (2026-09-11, per the user's follow-up
      request)**: `link_document_versions.py` extended with an optional
      `fold_en_iec_renumbering` mode on `version_group_key()` (folds
      `"EN IEC"` → `"EN"` for grouping only, mirroring the narrow
      `EIGA`/`IGC Doc` alias-fold style — never a blanket "drop every
      IEC"). A group is now accepted when it has either a real amendment
      marker (as before) OR a genuine EN/EN-IEC split among its members
      (`_has_en_iec_renumbering()`) — this split IS the structural
      evidence, playing the same role the amendment marker plays for the
      other shape, so no coincidental-core false positive risk. Ordering
      (no `platnost`/date reliance, same reasoning as `amendment_level()`)
      via new `version_sort_key()` = `(amendment_level, has_en_iec)` —
      an EN-IEC-renumbered designation is structurally never older than
      a plain "EN ..." sibling of the same part number. Re-running the
      grouping over the corpus found a **third** real pair by the same
      shape, not previously spotted: `STN EN 60079-14` (2016) → `STN EN
      IEC 60079-14` (2025) (near-identical annotation, same part number)
      — confirms the mechanism generalizes correctly, not just to the
      two originally-flagged cases. 12 new tests (240 total).
    - **`TNI CLC/TR 60079-32-1`/`STN CLC/TR 60079-32-1`: marked
      withdrawn (user's decision, 2026-09-11), kept as two separate
      records (not merged, not deleted, not renamed to the Czech
      equivalent — no ČSN record was added here, just the withdrawal
      note).** Per the user's research: the real, current document for
      this content is Czech — `ČSN CLC/TR 60079-32-1 (332320)`
      (confirmed valid at
      technicke-normy-csn.cz/csn-clc-tr-60079-32-1-332320-180776.html,
      an older/invalid catalog entry at the `-180775` variant of the
      same URL) — while neither the Slovak `TNI` nor `STN` designation
      appears to still be valid. Both records' `kategorie_trida`/
      `platnost` now say so explicitly and point to the real ČSN
      designation, same withdrawal-note style as `ISO 7105`'s follow-up
      #15 fix. One-time manual data correction, same PDF/XLSX-sourced-
      record limitation as before (patched in
      `sinay_normy_processed.json`).
  - **Re-run results (data/title fixes + withdrawal notes)**: full
    pipeline re-run. Deduplicated 1188→1191 (net, after the usual small
    LLM-merge non-determinism noise on the recurring `ISO 14687` cluster
    — unrelated to this pass's fixes, confirmed via diff). 230 tests
    still pass. `app/app.py` re-verified.
  - **Re-run results (EN-IEC version-linking extension)**: full pipeline
    re-run (`deduplicate_db.py` → `link_document_versions.py` →
    `init_db.py`). 20 version groups now (was 17) — the 3 EN-IEC pairs
    on top of the same 17 amendment pairs. Deduplicated 1191→1186 (3
    fewer top-level records, one per newly-linked pair, each collapsing
    2 flat records into 1). `h2regdocs` reloaded: 1209 `Document` rows
    (1186 + 23 bibliography),
    1229 `DocumentVersion` rows (1209 + 20 real second editions),
    spot-checked via SQL that `STN EN 60079-11`'s `DocumentVersion`
    rows are correctly version 1 (2012, not current) and version 2
    (`STN EN IEC 60079-11/ - 2025.03`, current). 240 tests total, all
    passing. `app/app.py` re-verified.
- **Follow-up #19 (2026-09-11): re-audited the "amendment pairs"/"EN-IEC
  renaming" and "coincidental generic-title" buckets once more for
  anything missed, and gave every orphaned amendment a durable,
  discoverable flag instead of leaving it silently unlinked.**
  - **Amendment pairs / EN-IEC pairs: nothing missed.** Checked every
    amendment-marked designation (27 total, including ones already
    inside a merged `versions` list) against the FULL corpus — not just
    its own jurisdikce — for a possible base match: the 17+3=20 already
    linked are correctly linked, the other 10 (`ČSN EN 13445-5+A1`,
    `STN EN 13136+A1`, `STN EN 16726+A1`, `STN EN 378-1/-3/-4+A1`, `STN
    EN 50465/A1`, `STN EN 88-3+A1`, `STN EN 1514-2+A1`, `DIN EN ISO
    11114-1/A1`) have no base anywhere in the corpus, in any
    jurisdikce — genuinely orphaned, not a missed-jurisdikce bug. Same
    exhaustive check for the EN/EN-IEC renumbering shape: no split
    beyond the 3 already linked, within or across jurisdictions.
  - **Coincidental generic-title bucket: 2 of 3 reconfirmed coincidental,
    1 turned out to be a real title bug, now fixed.**
    - `CGA G-5`/`OSHA 1910.103` (both titled "Hydrogen") and `CSA ANSI
      HGV 4.3`/`4.4` (both "Test methods for hydrogen fueling parameter
      evaluation") — reconfirmed genuinely different documents sharing a
      generic title, no new evidence either way (no internal
      contradiction found in either pair's own source data, unlike the
      case below).
    - **`DIN 50450-2`/`DIN 50450-9`: found and fixed a real title bug,
      same shape as follow-up #18's `IEC 62933-5-1` case.** Both records
      shared a byte-identical title AND the `-9` record's own annotation
      didn't match that title's stated topic (annotation described
      determining oxygen/nitrogen/CO/CO₂/hydrogen/hydrocarbons in
      hydrogen chloride by gas chromatography; the shared title
      described a completely different method — oxygen-in-N₂/Ar/He/Ne/H₂
      via galvanic cell). Root-caused directly in the raw XLSX (rows
      130/131): row 131's own German title column (correctly reads
      "…Teil 9: Bestimmung von Sauerstoff, Stickstoff,
      Kohlenstoffmonooxid, Kohlenstoffdioxid, Wasserstoff und
      C1-C3-Kohlenwasserstoffen in Chlorwasserstoff mit
      Gaschromatographie" — matching its own correct annotation) was
      never carried into the English title column, which instead still
      held row 130's (`DIN 50450-2`'s) title. Corrected the English
      title from a translation of row 131's own verified German text, in
      both the PDF- and XLSX-sourced occurrences (one-time manual data
      correction, same `sinay_normy_processed.json`-patch limitation as
      prior fixes). The two records are genuinely different DIN 50450
      series parts, now correctly distinguishable.
  - **New: orphaned amendments are now durably flagged, not just noted
    in this plan.** `link_document_versions.py` gained
    `find_orphan_amendments()`, writing every amendment-marked record
    that never joined a valid version group to the new
    `data/orphan_amendment_review_queue.json` (same review-queue
    convention as `dedup_review_queue.json`/`process_layer_review_queue.json`/
    `document_relations_review_queue.json`) — so the 10 orphans above
    are trackable for a future pass to go find/add their real base
    editions, rather than only living in this plan's prose. 4 new tests.
  - **Re-run results**: full pipeline re-run. Deduplicated 1186→1188
    (net, +2 from the usual `ISO 14687` LLM-merge non-determinism —
    unrelated to this pass, confirmed via the review queue still only
    flagging that one recurring cluster). 20 version groups unchanged,
    10 orphans written. `h2regdocs` reloaded: 1211 `Document` rows, 1231
    `DocumentVersion` rows. 244 tests total (4 new), all passing.
    `app/app.py` re-verified.

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

## 6. Requirements compliance checking (NEW, 2026-09-11)

`doc/REQUIREMENTS.md` (added 2026-09-11) lists 22 numbered requirements
(R1.1–R4.2) for the DP004 database/app. Since this needs re-checking after
every significant application change and every future edit to that file,
built a repeatable mechanism instead of a one-off manual review:

- **`src/tools/check_requirements.py`** (new) — mechanical, deterministic
  fact-gathering (DB schema/row-count queries + `app/` greps) for every
  requirement with a checkable answer. Reports raw evidence, never a
  verdict — see its own docstring and `src/tools/0README.md`.
- **`.claude/agents/requirements-check.md`** (new) — a project-local Claude
  Code subagent (`subagent_type: "requirements-check"`, invoked via the
  `Agent` tool) that re-reads `doc/REQUIREMENTS.md` fresh, runs the script
  above, adds the judgement calls the script deliberately doesn't make,
  and writes a full Markdown report to `doc/requirements_check_report.md`
  (overwritten each run — a current snapshot, same convention as
  `doc/similarity_analysis.md`). **Note**: a subagent defined mid-session
  isn't picked up by the already-running `Agent` tool's registry — it only
  becomes invokable by name after the Claude Code session restarts (or in
  a fresh session). The first report below was produced by hand, following
  the exact same procedure the agent definition specifies, as a substitute
  end-to-end verification.
- **First report** (`doc/requirements_check_report.md`, commit `12f24ca`):
  10 PASS, 6 FAIL, 4 PARTIAL, 1 N/A, 1 explicit mismatch (R3.2 — the
  requirements doc says SQLite; this repo settled on MariaDB back in Step
  0, see §5 above — an outdated requirements doc, not an open question).
  Two concrete, cheap, unrelated-to-any-single-requirement bugs surfaced
  along the way: `app/app.py`'s search query groups by `d.title` instead of
  `d.id` (R2.1 — would silently merge two real, different documents that
  happen to share a title, e.g. `CGA G-5`/`OSHA 1910.103`), and `wsgi.py`
  imports `Web.app` — a genuinely-importable but **deprecated,
  pre-migration, sqlite3-backed** app (`Web/app.py`, reading
  `Databaze/regulatory_documents.db` with an entirely different lowercase
  table-name schema) — not the canonical, actively-maintained
  `app/app.py` this whole pipeline builds for. Full detail, evidence, and
  a prioritized punch list (cheap fixes vs. bigger architectural
  decisions like R1.2's 3-tier jurisdiction categorization or R4.1's
  access control) are in the report file itself.
- **Both cheap fixes applied and verified (2026-09-11, commit `ebc1f60`)**,
  per the user's follow-up request: `app/app.py:81` now `GROUP BY d.id`
  (verified: `CGA G-5`/`OSHA 1910.103` now correctly return as 2 separate
  results, not 1); `wsgi.py` now `from app.app import app` (verified via
  direct import — also, `wsgi.py` turned out to have never actually been
  committed to this repo's git history before this fix). The report file
  was regenerated to reflect both as done. The user then manually removed
  `Web/Web.zip` (one of the two byte-identical duplicate archives —
  `app/Web.zip` still remains, untouched, in case only one was intended).
- **R1.2 (3-tier jurisdiction categorization) done, 2026-09-11.** Per the
  user's explicit wording: "national" must mean the actual national
  state (`CZ`, `DE`, `SK`, `PL`, ...), not an invented placeholder value —
  so this is an *additional* categorization layer, not a replacement for
  the existing, fine-grained `jurisdikce` column (still the veto this
  whole session's dedup work depends on to keep national adoptions of the
  same standard from merging). New `Document.jurisdikce_uroven
  ENUM('mezinárodní','EU','národní')`, a `GENERATED ALWAYS AS (...)
  VIRTUAL` column (MariaDB computes it automatically from `jurisdikce` on
  every read — no separate maintenance logic needed in `init_db.py`, and
  any future real country code, e.g. `PL`, automatically falls into
  `'národní'` with no code change). Mapping: `jurisdikce = 'mezinárodní'`
  → tier `'mezinárodní'`; `jurisdikce = 'EU'` → tier `'EU'`; any other
  non-empty, non-`'neurčeno'` value (a real country code) → tier
  `'národní'`; `NULL`/`'neurčeno'` → tier `NULL` — left honestly
  unclassified rather than force-guessed into one of the three tiers
  (184 of 1211 documents, 2026-09-11 — the same pre-existing
  unknown-jurisdikce residual, not a new gap). Verified via a full
  `init_db.py` TRUNCATE-and-reload (the generated column needs no special
  handling — it's simply absent from the INSERT column list and MariaDB
  computes it anyway) and a full pipeline re-run: `národní` 773,
  `mezinárodní` 198, `EU` 56, `NULL` 184. Schema change applied directly
  to the live `h2regdocs` and persisted in
  `doc/konsolidace/Konsolidace-DB-schema.sql`/`Konsolidace-DB-popis.md`
  §4.1. `src/tools/check_requirements.py`'s R1.2 section updated to also
  report the tier distribution. 244 tests still pass, `app/app.py`
  re-verified. `doc/requirements_check_report.md` updated: R1.2 now PASS.
- **R1.3/R1.4 (EU transposition / standard localization links) done,
  2026-09-11.** New `src/tools/link_document_relations_auto.py`, run
  before `init_db.py`, mechanically detects both shapes directly from
  `data/database_merged_deduplicated.json` and writes
  `data/document_relations_auto.json` (loaded by
  `load_document_relations.py`'s new `load_relation_sources()` alongside
  the existing hand-curated `data/document_relations.json`) plus
  `data/eu_transposition_missing_targets.json` for R1.3 candidates whose
  target isn't yet a `Document`. `document_relation.relation_type` gained
  `ADOPTS` alongside the existing `AMENDS`/`REPEALS`/`IMPLEMENTS`/
  `CONSOLIDATES`.
  - **R1.4 (`ADOPTS`)**: groups records by `international_core()` (strips
    national prefix, and a further "EN " layer only when immediately
    followed by ISO/IEC) and by jurisdikce tier; a group links only with
    at least one international/EU parent AND at least one national child,
    every child getting an edge to every parent. 17 real edges found and
    loaded (e.g. `STN EN ISO 11114-4/... ADOPTS ISO 11114-4`).
  - **R1.3 (`IMPLEMENTS`)**: for records whose OWN designation is NOT
    itself EU-act-styled (`is_eu_act_znacka()`), extracts every EU-act
    reference from `nazev_eu`/`odkaz_eu` (`finditer`, not just the first
    match — one citation text commonly names several acts) and links to
    the cited act if it already exists as its own record. **Design fix
    during this pass**: the citing-side filter deliberately does NOT use
    `jurisdikce`/`jurisdikce_uroven` — verified against the real corpus
    that `jurisdikce` is empty for BOTH national laws and EU acts alike in
    the `Sinay_Zakony`/`Haltuf_Dokumenty` sources, so a tier-based filter
    would have wrongly excluded the genuine national-law candidates too.
    The designation *shape* of the citing record is the only reliable
    signal — without it, an EU delegated/implementing act citing its own
    parent directive (e.g. `(EU) 2023/1184` citing `(EU) 2018/2001`) would
    produce a real but wrong-shape (EU-to-EU, not R1.3's national-to-EU)
    edge; found and excluded 4 such cases from the real corpus. Result: 0
    `IMPLEMENTS` edges yet (the cited EU acts — e.g. `2019/692`, `2018/858`
    — aren't in the corpus as their own records, a data-completeness gap,
    not a mechanism gap), 6 candidates written to
    `data/eu_transposition_missing_targets.json` for a future decision on
    whether to add those missing EU-act documents.
  - Verified: 24 unit tests in new `tests/test_link_document_relations_auto.py`,
    268 tests total pass, direct SQL confirms 17 `ADOPTS` + 1 pre-existing
    `AMENDS` = 18 rows in `document_relation`, 0 unresolved in the review
    queue, Flask smoke test OK. Documented in
    `doc/konsolidace/Konsolidace-DB-popis.md` §4.4 and
    `src/tools/0README.md`/`tests/0README.md`.
- **R1.5 (explicit lifecycle state) done, 2026-09-11.** New
  `DocumentVersion.lifecycle_state ENUM('active','superseded','draft')
  NOT NULL DEFAULT 'active'` — `is_current` (V01) is only a binary
  "is this the latest version" flag, not a state, as R1.5 requires.
  Deliberately NOT a `GENERATED` column (unlike R1.2's
  `jurisdikce_uroven`): the source text is the free-text `platnost` field
  (for versioned records, already carried into that version's own
  `effective_date` by `link_document_versions.py`), an unstructured,
  multilingual field, not a small controlled vocabulary — so classifying
  it is done in Python (`classify_lifecycle_state()` in
  `src/tools/init_db.py`, unit-tested) at import time, same convention as
  `resolve_document_type()`. Rule: `is_current = FALSE` → always
  `'superseded'` (a replaced version, regardless of its own platnost text
  at the time); `is_current = TRUE` and the text carries a real
  draft/work-item marker → `'draft'`; otherwise → `'active'`. Real marker
  strings verified directly in the corpus (German/Czech/Slovak
  standards-body terminology): `"Entwurf"`/`"Návrh"` (draft),
  `"Arbeitsdokument"`/`"pracovný dokument"` (work item), `"PWI"`
  (ISO/IEC Preliminary Work Item stage) — deliberately NOT the broader,
  looser guesses tried during exploration (`"pripravovan"`,
  `"rozpracovan"`, `"ve schvalov"` never actually appear in this corpus).
  Verified: 8 new unit tests in `tests/test_init_db.py` (26 total in that
  file), 273 tests total pass, schema change applied directly to the live
  `h2regdocs`, full `init_db.py` reload confirms real corpus distribution
  `active` 1035 / `draft` 153 / `superseded` 20 (of 1208 `DocumentVersion`
  rows) — a substantial, genuinely-evidenced draft population, not a
  handful of edge cases. `document_relation`/`node_document` FK-dependent
  rows survived the reload unchanged (deterministic re-import order keeps
  `Document.id` stable). `check_requirements.py`'s R1.5 section extended
  to report the state distribution. Flask smoke test OK. Documented in
  `doc/konsolidace/Konsolidace-DB-popis.md` §4.3 and
  `src/tools/0README.md`/`tests/0README.md`.
- **R1.7/R4.1 (populate file_path + enforce access control) done,
  2026-09-11.** `Document.file_path` existed but was 0% populated and
  never even selected by `app/app.py`. New `resolve_file_path()` in
  `src/tools/init_db.py` populates it from `data/fulltext_manifest.json`
  (built by `fetch_fulltext.py`) — for a merged record, every contributing
  source in its comma-joined `zdroj_dat` is tried against every URL field.
  Never guessed: no manifest hit means `NULL`, same as today.
  New `DocumentType.restricted_fulltext BOOLEAN` (`TRUE` only for
  `"Norma"`) is the actual R4.1 enforcement mechanism — deliberately NOT
  inferred from "file_path happens to be empty", because that turned out
  to be unsafe in practice: verifying this surfaced a real gap in
  `fetch_fulltext.py`'s own norm exclusion — its `NORM_SOURCES` blocklist
  checks only the RAW record's `zdroj_dat`, and `Haltuf_Dokumenty` (a law
  source) turned out to also carry a handful of stray norm citations of
  its own (`ISO 14687`, `ČSN EN 17127`, `DIN EN ISO 22734`, ...), so 2
  Documents that resolved to type `"Norma"` had already gotten a
  `file_path` before this fix. Inspected both cached files directly:
  harmless in this instance (public e-shop/anti-bot pages, not paid
  normative text), but the wrong content shape regardless, and proof the
  flag-based gate is load-bearing, not just theoretical. Fixed the root
  cause too: `fetch_fulltext.py` gained `is_norm_designation()`, a second,
  source-independent check on the designation's own shape (same precedent
  as `link_document_relations_auto.py`'s `is_eu_act_znacka()`), so a
  future rerun won't repeat this.
  New `app/app.py` route `/fulltext/<id>` is where the gate actually
  lives: looks up `file_path` + `restricted_fulltext` fresh on every
  request (never trusts template-render-time state), returns 404 with no
  `file_path`, 403 when restricted, and validates the resolved path stays
  inside `data/fulltext/` before `send_file()` (defense in depth against
  path traversal, even though `file_path` only ever comes from our own
  manifest). `index.html` shows a "Stažená kopie" link only when
  `file_path` is set AND `restricted_fulltext` is false.
  Verified: 11 new unit tests (`tests/test_init_db.py`,
  `tests/test_fetch_fulltext.py`) + 4 new integration tests in
  `tests/test_search.py` exercising the real live-DB route (confirmed 403
  for the 2 real restricted-with-file_path Documents, 200 for an open
  law, 404 for no-file_path and for a nonexistent id) — 288 tests total
  pass. Real corpus after reload: 69/1188 Documents with `file_path`, 67
  open + 2 restricted (both correctly 403'd). `check_requirements.py`
  extended (R1.7's DB section now also reports the
  `restricted_fulltext` distribution; R4.1 greps `app/app.py` for the new
  route/gate). Documented in `doc/konsolidace/Konsolidace-DB-popis.md`
  §4.1/§4.5 and `src/tools/0README.md`/`tests/0README.md`.
- **R2.5 (CSV/JSON/XML export) done, 2026-09-11.** New `app/app.py` route
  `/export/<fmt>` (`fmt` in `{csv, json, xml}`, `abort(400)` otherwise) —
  exports the current filtered/searched result set (same `q`/`type_id`/
  `source_id`/`keyword_id` params as `index()`), but the FULL filtered set,
  not the on-screen `LIMIT 100` page. `index()`'s filter-parsing and
  query-building logic was refactored out into shared, testable helpers
  (`parse_filters()`, `build_document_query()` — pure, no DB access,
  `limit=None` vs `limit=100` — and `fetch_documents_with_tags()`) so both
  routes apply identical filtering without duplicated SQL.
  **Metadata-only per R4.1**: `_rows_for_export()` projects each row down
  to exactly `title, description, type_name, source_name, language,
  effective_date, url, keywords` — deliberately excludes `file_path`,
  `restricted_fulltext`, and `id` (that's the separate, gated
  `/fulltext/<id>` channel; bulk export must never carry a local file
  path). Response builders are stdlib-only (`csv`+`io.StringIO`,
  `json.dumps` via a plain `flask.Response` for header control, and
  `xml.etree.ElementTree`), each with the correct `mimetype` and a
  `Content-Disposition: attachment` download header. Template
  (`index.html`) gained 3 links (CSV/JSON/XML) next to "Reset Filtry",
  reusing the existing `.btn-secondary` style — no new CSS.
  Verified: 11 new pure unit tests (new `tests/test_app_export.py` —
  `build_document_query`'s `limit=None` vs `limit=100` behavior, and
  `_rows_for_export`'s output-key guard) + 6 new integration tests
  (`tests/test_search.py`'s new `ExportRouteTestCase` — each format 200
  with correct content-type, invalid format 400, a `type_id` filter
  measurably reduces the exported row count, and a regression guard
  parsing each format's real response body to confirm no `file_path`/
  `restricted_fulltext`/`id` ever appears) — 305 tests total pass. Real
  corpus: unfiltered export returns all 1188 documents (not capped at
  100), confirming the export ignores the UI page-size limit as intended.
  `check_requirements.py`'s R2.5 section now reports real `csv`/`export`/
  `xml` hits in `app/app.py`/`index.html` (previously "(none)").
- **R3.2 (SQLite-vs-MariaDB wording mismatch) resolved, 2026-09-11.**
  `doc/REQUIREMENTS.md` updated to say "currently implemented as MariaDB"
  (was "SQLite") — the project settled on MariaDB back in early pipeline
  work (see §5 above); this was a stale-doc fix, not a code change, per
  the user's explicit choice (update the doc to match reality, rather
  than record MariaDB as a "deviation" from an unchanged doc).
  `check_requirements.py`'s R3.2 section updated to read the actual
  current wording from `doc/REQUIREMENTS.md` instead of hardcoding
  "SQLite", so it won't go stale again if the doc changes further.
- **`app/Web.zip` removed, 2026-09-11.** The user confirmed they intended
  to delete this earlier but it was still on disk (122774 bytes) —
  confirmed untracked and gitignored (`.gitignore` line 16) before
  removing, so this was a plain filesystem `rm`, no git history involved.
  This closed out the requirements-compliance punch list as it stood at
  the time (see `doc/requirements_check_report.md`) — R1.3/R1.4's own
  data-completeness follow-up (below) was raised separately afterward.
- **R1.3 data-completeness gap closed, 2026-09-11: the 6 missing EU-act
  `Document` rows were added.** `data/eu_transposition_missing_targets.json`
  named 6 real EU acts (directives/a regulation/an implementing decision)
  cited by 3 national laws already in the corpus (`201/2012 Sb.`,
  `56/2001 Sb.`, `458/2000 Sb.`) but missing as their own records — each
  verified individually against eur-lex.europa.eu (official title, act
  type, adoption date, CELEX number, plus the official Czech-language
  title and Official Journal reference) before being added, never
  guessed. New source `data/eu_transposition_targets.json`, wired into
  `build_unified_db.py` as a 6th source exactly like V02 Bibliography.
  Real data-quality finding surfaced during verification: the citing
  record for `56/2001 Sb.` mislabels `(EU) 2018/858` as a "směrnice"
  (directive) — confirmed via EUR-Lex (CELEX 32018R0858, and its own
  Czech-language text) that it's actually a **Regulation**; the new
  `Document` row uses the correct type (`Nařízení EU`), the pre-existing
  citing text was left untouched (out of scope). Result: R1.3 now has 6
  real `IMPLEMENTS` edges (`AMENDS` ×1, `IMPLEMENTS` ×6, `ADOPTS` ×15),
  `eu_transposition_missing_targets.json` is empty.
  - **A real, more serious bug was found and fixed along the way**: the
    full pipeline re-run needed for this addition (`build_unified_db.py`
    → `deduplicate_db.py` → ...) unexpectedly merged an international
    `ISO 14687` (jurisdikce `mezinárodní`) into a Czech `ČSN ISO 14687`
    (jurisdikce `CZ`) — exactly the cross-jurisdiction merge this whole
    pipeline's jurisdikce veto exists to prevent. Root cause:
    `build_clusters()`'s jurisdikce-conflict veto was checked only
    *pairwise* (`_jurisdikce_conflict(i, j)`) — a record with an unknown/
    blank jurisdikce individually conflicts with neither a known-CZ nor a
    known-"mezinárodní" record, so Union-Find transitivity could silently
    bridge two correctly-vetoed, directly-conflicting islands *through*
    it. Real trigger: several `Haltuf_Dokumenty` rows ("ISO 14687"/"ČSN EN
    ISO 14687") carry a blank jurisdikce and bridged `Sinay_Normy`'s
    "mezinárodní" ISO 14687 into `Prokop_Normy`'s "CZ" ČSN ISO 14687 in
    this run — non-deterministic (this same latent bug has presumably
    existed since Krok 1, only sometimes masked by GPT-4o-mini's own
    unreliability at actually collapsing such a mixed-jurisdikce cluster,
    see `is_pure_znacka_cluster`'s docstring). Fixed by checking the
    conflict at the **island** level instead of the pair: `_try_union()`
    tracks each island's current set of known jurisdikce values and
    rejects a union if combining two islands would ever exceed size 1 —
    closing the transitivity loophole regardless of processing order.
    New regression test
    `test_bridging_unknown_jurisdiction_record_never_joins_two_known_conflicting_islands`
    in `tests/test_deduplicate_db.py` reproduces the exact bug (fails
    before the fix, passes after). Re-verified against the real corpus
    post-fix: `ISO 14687` (mezinárodní) and `ČSN ISO 14687` (CZ) correctly
    remain separate `Document` rows; `dedup_review_queue.json` empty.
  - Verified: 306 tests total pass (1 new regression test), full pipeline
    re-run end to end (`build_unified_db.py` → `deduplicate_db.py` →
    `link_document_versions.py` → `init_db.py` →
    `link_document_relations_auto.py` → `load_document_relations.py` →
    `load_process_layer.py`), `process_layer_review_queue.json` unchanged
    (still only the 2 known, previously-reviewed `EN ISO 17268`
    ambiguity items), `check_requirements.py`'s R1.3 section confirms `6`
    `IMPLEMENTS` rows, Flask smoke test OK. Documented in
    `doc/konsolidace/Konsolidace-DB-popis.md` §4.4,
    `src/tools/0README.md` (`build_unified_db.py` and `deduplicate_db.py`
    entries), `tests/0README.md`, and `doc/requirements_check_report.md`
    (R1.3 now PASS).

## 7. Data-quality flagging — needs_review (NEW, 2026-09-11)

User found this by using the new R2.5 export: some catalog entries have a
meaningless title/znacka and/or no description at all — e.g. a `"Norma"`
with `znacka` `"CEN/TC 326 Natural Gas Vehicles"` (a technical-committee
name, not a designation) and `nazev_cz` `"- Fuelling and Operation"` (an
orphaned continuation fragment), empty description. Root cause: a real,
narrow parsing bug in `parse_sinay_norms.py`'s coordinate-based PDF-table
reconstruction — a single wrapped line split across the wrong columns.
Explicit instruction: never silently show/export a record like this —
flag it for manual intervention, but (per the user's explicit choice,
over hiding it) keep showing it in search/export with a visible marker.

- New `src/tools/init_db.py` functions, all pure/unit-tested:
  `is_garbled_znacka()` (bare edition-date suffix like `"- 2024.09"`, or a
  bare `CEN|CENELEC|ISO|IEC/TC` committee reference), `is_fragment_title()`
  (starts with a stray dash/colon or a `"N-N:"` part fragment, or is
  lowercase-starting text that isn't a legitimate lowercase Czech/Slovak
  legal-title convention like `"zákon č. ..."`/`"vyhláška č. ..."` —
  excluded explicitly so real law titles are never mistaken for
  fragments), and `detect_data_quality_issues()` combining both plus a
  missing-description check into a list of Czech-language reasons.
- New `Document.needs_review BOOLEAN` / `review_reason VARCHAR(500)`,
  computed at import time (same pattern as `lifecycle_state`/
  `restricted_fulltext` — never a `GENERATED` column, since detection
  needs real string-shape logic, not a small controlled vocabulary).
  `init_db.py` also writes every flagged record to new
  `data/incomplete_records_review_queue.json` (same convention as every
  other `*_review_queue.json` in this pipeline) — detection never
  guesses/repairs a fix, only flags for a human.
- `app/app.py`'s shared `build_document_query()` now also selects
  `needs_review`/`review_reason`; `index.html` renders a visible
  "Vyžaduje kontrolu" badge (new `.review-flag` CSS class, matching the
  existing `.meta-tag`/`.keyword-tag` look) with `review_reason` as its
  tooltip — the record itself is NOT hidden or excluded from search/
  export, exactly as the user specified. `_rows_for_export()`'s explicit
  `EXPORT_FIELDS` whitelist means these two new columns never leak into
  CSV/JSON/XML exports (out of scope for this pass — the ask was about
  the browsable catalog, not the export payload).
- Verified: 13 new unit tests, 319 tests total pass, real corpus (2026-
  09-11): 411/1192 documents flagged (409 missing description, 14
  fragment titles, 8 garbled znacka — some overlap, e.g. the two examples
  above carry all three). Flask smoke test confirms the badge renders
  with the correct tooltip text; export confirmed clean of the two new
  fields. Documented in `doc/konsolidace/Konsolidace-DB-popis.md` §4.1,
  `src/tools/0README.md`, `tests/0README.md`.

**Root cause fixed, 2026-09-11** (user's explicit follow-up request: "try
to actually fix the `parse_sinay_norms.py` column-misalignment bug", not
just flag its symptoms). Traced both real garbled-znacka examples to two
distinct bugs in the PDF-table reconstruction:

1. **A later section of the source PDF (pp. 81-83) isn't the standards
   table at all** — it's an appendix listing the technical committees
   relevant to hydrogen (e.g. `"CEN/TC 326 Natural Gas Vehicles -
   Fuelling and Operation https://..."`), reusing the exact same column
   template. A committee reference's whole "code + scope description" is
   really ONE run-on text with no genuine column break, but since it's
   long, some of it spills past the designation/title boundary (x=175),
   producing a bogus fragment title instead of the empty title that
   would let the module's own existing, already-documented filter
   (`if row["title"].strip():` in `parse_pdf()`) correctly drop it as
   "not a document" — dropping title-less rows was always the intended
   handling for exactly this row shape, it just wasn't reliably
   triggering. New `_COMMITTEE_REFERENCE_RE` (`^(ISO|IEC|CEN|CENELEC|
   CLC)/TC\s+\d+`) detects this designation shape and clears the bogus
   title so the existing filter fires — verified against the real PDF:
   15 such committee-reference lines total, 0 leak through after the fix
   (most were already correctly dropped since their description was
   short enough to stay within the designation column; only the longer
   ones, 6 of the 15, were actually bugged).
2. **The trailing "/ - YYYY.MM" edition-date suffix wraps inconsistently**
   — sometimes the dash stays with the designation
   (`"...15502-3-1/ -"` + `"2024.08"`), sometimes it wraps onto the
   continuation line instead (`"...62443-1-5/"` + `"- 2024.09"`).
   `merge_designation_continuations()`'s `_DATE_FRAGMENT_RE` only matched
   the first (bare `"YYYY.MM"`) shape — broadened to `^-?\s*\d{4}\.\d{2}$`.
   Without this, the leading-dash continuation started a bogus new row,
   which then stole the TRUE row's own wrapped title continuation
   (`"1-5: Schéma pre bezpečnostné profily IEC 62443"`) — exactly the
   second real example the user reported.

**A separate, important discovery while fixing this**: rerunning
`parse_sinay_norms.py` naively would have silently destroyed ~11 real,
valuable hand-curated corrections already accumulated in
`data/20250712_Sinay/sinay_normy_processed.json` earlier in this session
(e.g. the `DIN 50450-9` title fix, a cancelled/superseded-norm
cross-reference for `STN 65 1312-2`/`ISO 7105`) — that file is a
hand-enriched artifact, not a pure function of the raw PDF/XLSX + parser
code, and a full regeneration would have reverted all of it back to the
parser's raw output. Caught this by diffing a fresh parse against the
git-committed file *before* trusting a full regeneration, then applied
the fix surgically: patched only the 8 affected records directly (merged
the 2 date-continuation pairs, removed the 6 committee-reference rows)
in the existing hand-curated file, leaving every other record — including
all 11 prior manual corrections — untouched.

Verified: 2 new regression tests in `tests/test_parse_sinay_norms.py`
(`ParsePdfPageTestCase`, end-to-end against a fake `pdfplumber.Page`
reproducing the exact real word layouts that broke) + 1 new
`MergeDesignationContinuationsTestCase` case, 40 tests in that file, 322
tests total pass. Full pipeline rerun (`build_unified_db` →
`deduplicate_db` → `link_document_versions` →
`link_document_relations_auto` → `init_db` → `load_document_relations` →
`load_process_layer`) — `dedup_review_queue.json` clean, the R1.3/R1.4
edge counts (6 `IMPLEMENTS`, 15 `ADOPTS`) and the R1.5-era `ISO 14687`/
`ČSN ISO 14687` jurisdikce separation both hold. Real corpus after the
fix: `needs_review` count dropped from 411/1192 to 402/1183 — garbled-
znacka flags went from 8 to 0 (both real cases now genuinely fixed, not
just flagged), fragment-title flags from 14 to 7 (the remaining 7 are a
different, not-yet-diagnosed root cause — still correctly caught by the
flagging mechanism, which is exactly its intended fallback role).
Flask smoke test confirms the fixed record now shows its full, correct
title and the old bogus committee-reference title is gone entirely from
search. Documented in `src/tools/0README.md`, `doc/konsolidace/
Konsolidace-DB-popis.md` §4.1, `doc/requirements_check_report.md`.

## 8. Authoritative per-site title/description extraction (`src/sites/`, NEW, 2026-09-11)

User's proposal: instead of relying on the Haltuf/Sinay/Prokop spreadsheet
exports for title/description (the direct cause of most `needs_review`
cases, §7 above), fetch the canonical title/description directly from each
document's own "single point of authority" website, via a small dedicated
parser per site. Extends §4 (full-text acquisition) with a parsing layer,
and closes §5's long-open "Document-parsing sub-layer" decision (scoped
down to a concrete, non-agentic implementation, not the full §3 LangGraph
architecture).

**Feasibility research first** (two Explore passes against the real
corpus + live fetch tests, before any code): of 1183 records, 124 (10.5%)
have no usable URL at all. Of the rest, the large majority of NORM records
store only a generic organization homepage or catalog root — `normy.
normoff.gov.sk` (374 recs, 100% the same root URL), `www.dvgw.de` (102,
100% homepage), `www.iso.org` (129/136 sharing one generic
`/standards.html` URL), `www.eiga.eu` (33, 100% homepage), and ~15 more
domains in the same shape — no per-document parser can help these; the
stored URL doesn't even identify which document it's for. **Decision:
explicitly out of scope.** Domains that DO carry genuine per-document
URLs, with scrapeability confirmed live: `eur-lex.europa.eu` (~43 law
records + 6 `EU_Transposition_Targets`), `zakonyprolidi.cz` (~35 law
records), `slov-lex.sk` (~5), and `Prokop_Normy`'s ~33 ČSN-designated norm
records via the already-existing `check_csn_validity.py` registry
(`csnonline.agentura-cas.cz` — free, not anti-bot-walled, unlike
`technicke-normy-csn.cz`, confirmed anti-bot-walled with "BotStopper" and
never targeted). ~120 records addressable this pass.

**e-Sbírka detour, found while implementing**: the user asked to prefer
`e-sbirka.gov.cz` (the real government source) over `zakonyprolidi.cz` (a
private mirror) "where possible." Investigated live: `e-sbirka.gov.cz`'s
own frontend is an unscrapeable Angular SPA (`<esel-app>` empty shell, no
server-rendered content at all); its REST API requires Ministry-of-Interior
client registration (already documented in `screen_esbirka.py`); its
public LOD SPARQL graph (`opendata.eselpoint.gov.cz`) does expose a
per-law node addressable by ELI (constructible directly from a Czech
znacka), and DOES confirm the official citation — but traced several
levels into the `slovník.gov.cz/datový/sbírka` graph and found the actual
title text lives nowhere as a simple field: it's structured at the
individual-paragraph-fragment level (hundreds of nodes per law), not as a
document-metadata record. **Resolution** (user's explicit call):
`zakonyprolidi.cz` stays the content source; `src/sites/esbirka.py`
verifies the citation and attaches the real government URL
(`https://e-sbirka.gov.cz/sb/{year}/{number}`) as a `zdroj_esbirka_url`
reference alongside it — never replacing the actual title/description
text. `REST_API_TODO` comment left in that module: once a registered
e-Sbírka REST API key is obtained, it's the natural place to extend into
a full content source (same `{"title", "description"}` return shape).

**Design implemented:**
- New package **`src/sites/`** — one module per domain, common interface
  `extract(url, cached_path=None, session=None) -> {"title", "description"} | None`
  (never raises, `None` on any failure):
  - `eurlex.py` — resolves a CELEX id from the URL (only when the URL
    carries one explicitly, `?uri=CELEX:...`; ELI-style/OJ-style URLs
    deliberately left unresolved, no guessing), queries the public
    EUR-Lex Cellar SPARQL endpoint (same one `screen_eurlex.py` already
    uses) for `cdm:expression_title`, preferring Czech over English.
    Real bug found & fixed while testing against the live endpoint: the
    CELEX literal in the query MUST carry an explicit `^^xsd:string`
    datatype annotation, or the query silently returns nothing — even for
    a CELEX confirmed to exist via a keyword search.
  - `zakonyprolidi.py` — parses `<meta property="og:title">`/`<meta
    property="og:description">` (already-cached HTML under
    `data/fulltext/{Haltuf_Dokumenty,Sinay_Zakony}/` preferred over a
    live fetch). Verified live: no anti-bot wall — an earlier
    WebFetch-tool-only 403 turned out to be a tool-specific artifact.
  - `slovlex.py` — parses the `<script type="application/ld+json">`
    schema.org `Legislation` block's `name` field (the rendered page is
    an Angular SPA with no server-rendered body text, but this JSON-LD
    metadata IS present); falls back to `<title>`.
  - `esbirka.py` — verification-only, see above.
- New **`data/site_metadata_cache.json`**: small, git-tracked, keyed by
  URL (or `"csn:<znacka>"` for ČSN lookups with no per-document URL of
  their own). Idempotent.
- New **`src/tools/fetch_authoritative_metadata.py`**: dispatches
  eligible records from `data/database_merged_raw.json` to the matching
  `src/sites/*` module or `check_csn_validity.py`, writes results into
  the cache. `--limit`/`--force` flags, same convention as
  `fetch_fulltext.py`. Never writes into any `database_*.json` directly.
- **`build_unified_db.py`** (`apply_authoritative_metadata()`, run at the
  end of every build, after all 6 sources): attaches
  `nazev_autoritativni`/`popis_autoritativni`/`zdroj_autoritativni_url`
  as NEW, separate fields when the cache has a fetched entry for a
  record's URL — never overwrites `nazev_cz`/`anotace_poznamka` (avoids
  language-mismatch surprises, keeps the original auditable). Applied
  here, at the END of every rebuild, so it survives every rebuild
  automatically — this is exactly the trap found and worked around this
  session for `enrich_annotations.py`'s edits (its `previous_annotations`
  restore mechanism reads from `database_merged_raw.json`'s own previous
  run, keyed by `zdroj_dat`+`nazev_cz` — NOT from
  `database_merged_deduplicated.json`, so any edit made there is silently
  discarded on the next raw rebuild; `enrich_annotations.py` itself
  confirmed never actually run against the live corpus, still dormant).
- **`init_db.py`**: new `resolve_title()`/`resolve_description()` prefer
  the authoritative fields, falling back to today's resolution
  unchanged. Used both for the actual `Document.title`/`description`
  columns AND inside `detect_data_quality_issues()` — a record whose
  original `nazev_cz` is garbled but has a real authoritative title is no
  longer flagged.

**Verified**: 61 new unit tests (`tests/test_sites_*.py` ×4,
`tests/test_fetch_authoritative_metadata.py`, plus additions to
`tests/test_build_unified_db.py`/`tests/test_init_db.py`) — mocked
HTTP/SPARQL, no real network calls in the suite — 383 tests total pass.
Full live run against the real corpus: 143 cache entries, 107 with a real
title (35/35 `zakonyprolidi`, 27/33 `csnonline`, 4/5 `slovlex`, 41/70
`eurlex` — the `eurlex` shortfall is entirely the documented ELI/OJ-style
URLs this pass deliberately doesn't resolve, not a failure). Full
pipeline rerun (`build_unified_db` → `fetch_authoritative_metadata` →
`deduplicate_db` → `link_document_versions` →
`link_document_relations_auto` → `init_db` → `load_document_relations` →
`load_process_layer`) — `dedup_review_queue.json` clean, R1.3/R1.4 edge
counts and the ISO 14687/ČSN ISO 14687 jurisdikce separation both hold.
Flask smoke test and a direct DB spot-check both confirm a real,
end-to-end win: `458/2000 Sb.`'s `Document.title` now reads
`"458/2000 Sb. Energetický zákon"` (the verified zakonyprolidi.cz title),
not whatever the spreadsheet happened to carry.

**Honest finding on `needs_review`, checked directly rather than
assumed**: this pass does **not** reduce the 402-record `needs_review`
count. The ~120 addressable records (laws + `Prokop_Normy`'s ČSN norms)
turn out to barely overlap with the currently-flagged set at all — the
flagged 402 are effectively all `Sinay_Normy` (missing description) plus
a handful of still-undiagnosed fragment titles, entirely outside this
pass's scope; the law/ČSN records were already "clean" by the review
heuristics (0 of either population showed up flagged, verified directly,
not inferred). The real value delivered here is different from what was
originally expected: **verified, source-confirmed data** replacing
"whatever the spreadsheet said" for 107 records, plus the reusable
`src/sites/` infrastructure for future expansion — not a review-queue
size reduction. Documented honestly rather than restating the original,
disproven expectation.

**Not done this pass** (future work, not requested): extending to more
domains, a "search the site by designation" mechanism for the ~650+
generic-catalog-root norm records (a substantially bigger, differently-
shaped undertaking), reviving `enrich_annotations.py` as an LLM-based
fallback tier, migrating `esbirka.py` to a real content source once a
REST API key is obtained.

**Manual spot-check against live sources (2026-09-11), requested by the
user beyond the automated test suite**: a random sample per domain from
`data/site_metadata_cache.json` was re-verified against fresh live
fetches/queries (not just re-reading the cache).

- `eurlex`: re-ran the Cellar SPARQL query live for CELEX `32019R0942` —
  returned title matches the cached value character-for-character.
- `zakonyprolidi`: re-fetched `192/2022 Sb.`'s live page. Its title in the
  cache ends in "..." — confirmed this is **not** a truncation artifact of
  our own code: the site's own `og:title` meta tag genuinely ends in
  "..." (the CMS truncates long titles for SEO). The `og:description` is
  separate and carries the full, untruncated text, so no information is
  actually lost.
- `slovlex`: re-fetched `699/2004 Z. z.`'s live page (redirect chain to
  `/ezbierky/...` followed). The JSON-LD `Legislation.name` matches the
  cached value exactly.
- `csnonline`: found one real, low-frequency defect. `fetch_csn_metadata()`
  picks the *first* search result whose designation matches exactly; for
  a standard with multiple historical editions under the same designation,
  "first" isn't guaranteed to be the most recent or currently-valid one.
  Re-checked all 27 cached ČSN entries against fresh live searches: 24/27
  unaffected (single edition, or identical title text across editions).
  Of the remaining 3, two "more recent" rows are actually amendment/errata
  stubs (`Změna ke stažení: Z1...`) — picking "first" accidentally avoided
  junk there. The third, `ČSN EN ISO 17268`, is a genuine miss: the cache
  holds the 2017 edition's title ("Plynný vodík - Plnicí rozhraní
  pozemních vozidel", withdrawn 2020) instead of the 2022 edition's
  ("Plynný vodík - Spojovací zařízení pro doplňování paliva pro pozemní
  vozidla na plynný vodík") — and neither is actually current any more,
  since the designation itself was later retired and split into
  `ČSN EN ISO 17268-1`. **Decision (user's explicit call): leave as-is.**
  A robust fix would need to distinguish real edition rows from
  amendment/errata rows before picking "most recent," and there is no
  reliable way to know which historical edition the source spreadsheet's
  `znacka` actually intended — not worth the added complexity for the one
  affected record found in the current corpus.

## 9. `agentura-cas.cz` as the single point of authority for ČSN standards (NEW, 2026-09-13)

Follow-up to §8: the user asked how big a "search by designation" job
would be for Czech national norms specifically, suspecting
`technicke-normy-csn.cz` (§8's original ČSN domain, confirmed anti-bot-
walled, never touched directly) is an independent third-party mirror —
and asked to check `csnonline.agentura-cas.cz` (already integrated) and
`seznamcsn.agentura-cas.cz` (not yet investigated) as the real "single
point of authority." Confirmed live: both are the actual national
standards body (Česká agentura pro standardizaci, formerly ÚNMZ),
near-identical ASP.NET backends, `technicke-normy-csn.cz` genuinely
independent. Once sized, the user asked to actually build it: use
agentura-cas.cz throughout, re-fetch everything, and — for a record
whose corpus `znacka` is a bare EN/ISO/IEC designation — represent BOTH
the international original (its own title) AND the Czech national
adoption (its own title, with a reference back to the original) as two
separate documents, "if it exists."

**Key new source found**: `Detailnormy.aspx?k=<katalogové číslo>` — a
stable, per-standard, GET-able detail page (same on both agentura-cas.cz
sites), with clean `<span id="...">`-labeled fields: `oznaceni` (Czech
designation), `nazev` (Czech title), `nazeven` (**English title** — the
"original"), and a `GridView2` table of `{Označení, Rok vydání}` under
"Zapracované dokumenty" — the registry's own explicit link from a
national adoption back to the international standard(s) it adopts.
`check_csn_validity.fetch_detail()` parses this by catalog number, taken
from a `search()` result's own `catalog_number` field.

**`check_csn_validity.py`** also gained `find_best_match()`, replacing
the old "first exact match wins" logic with formatting-tolerant matching
(`strip_catalog_suffix()` for a trailing `(336000)`-style suffix,
`split_edition()` for `ED.2` ↔ `ed. 2` spacing/case differences) and a
prefer-valid-else-most-recent-real-edition tie-break (excluding
amendment/errata title rows like `Změna ke stažení...`) applied
uniformly whether the match was exact or base-only — this is the general
fix that also resolves the `ČSN EN ISO 17268` case §8 left as an
explicit "leave as-is" exception (confirmed and accepted, not a silent
side-effect: the general logic is simply more correct).

**`fetch_authoritative_metadata.py`**: `is_csn_norm_record()` widened
from `Prokop_Normy`-only, ČSN-prefix-only to also cover
`Haltuf_Dokumenty`/`Sinay_Normy` and bare EN/ISO/IEC designations (the
corpus's own citation of the international original, "not yet/never
separately ČSN-numbered"). `fetch_csn_metadata()` now also retries a
corpus-side "spurious EN" mistake (`ČSN EN ISO 19880-1` → real
designation `ČSN ISO 19880-1`, confirmed live on both agentura-cas.cz
sites) as a last-resort fallback — found to apply to BOTH bare and
already-ČSN-prefixed znacka, not just bare ones as first assumed. For a
bare/international match: this record's own `nazev_autoritativni`
becomes the **English** title (refers to the original) and
`jurisdikce_autoritativni` is set to `"mezinárodní"` (bare ISO/IEC) or
`"EU"` (bare EN, with or without a following ISO/IEC — same
CEN/CENELEC-level tier as `build_unified_db.py`'s existing EN-ISO/EN-IEC
handling); if agentura-cas.cz confirms a Czech adoption exists, a
`synthesize` block is written unconditionally (see below for why not
conditionally) so `build_unified_db.py` can add that second document.

**`build_unified_db.py`**: `resolve_prokop_jurisdikce()` had a real,
narrowly-scoped bug found along the way — a bare `EN <number>` with NO
following ISO/IEC (e.g. `EN 17127`) fell through both existing regexes
and defaulted to `"CZ"`, when it's actually the CEN/CENELEC original
(`"EU"`), exactly like the already-handled `EN ISO`/`EN IEC` case. Fixed
(`_BARE_EN_DESIGNATION_RE`). `apply_authoritative_metadata()` now also:
prefers the cache's real `zdroj_autoritativni_url` (the actual
`Detailnormy.aspx` page) over `record_url()`'s spreadsheet-derived
fallback — fixing a real gap where a ČSN record's provenance URL
silently fell back to the record's own (often third-party) URL, since
`fetch_csn_metadata()` never used to return one at all; and applies
`jurisdikce_autoritativni` directly to `record["jurisdikce"]` when it
differs (keeping the original under `jurisdikce_puvodni` for audit — the
one place in this pipeline where an authoritative field IS applied
in-place rather than kept side-by-side, because `jurisdikce` is read
as-is by `deduplicate_db.py`/`link_document_relations_auto.py` and a
stale value there silently breaks the `ADOPTS` auto-linking, not just
display). New `synthesize_csn_adoption_records()`: for every cache entry
carrying a `synthesize` block, appends a new minimal record if no
existing record in `unified_db` already carries that exact znacka —
idempotent by construction against the FRESH `unified_db` built from the
6 real sources every run (see the bootstrapping bug below for why this
must be the sole gatekeeper, not `fetch_authoritative_metadata.py`).

**Two-documents-plus-a-relation is not new infrastructure** — confirmed
by research before implementing: `document_relation.relation_type`
already has an `ADOPTS` value exactly for this ("ISO 14687/ČSN ISO 14687
jurisdikce separation", §6), `deduplicate_db.py` already refuses to merge
across a jurisdikce conflict (an international standard and its national
adoption stay two separate `Document` rows forever), and
`link_document_relations_auto.py`'s R1.4 `find_localization_pairs()`
already, mechanically, groups by `international_core(znacka)` +
`jurisdikce_tier()` and emits `ADOPTS` from every national member to
every international/EU member of its group — **with zero changes needed
to that script**, since it already excludes a blank jurisdikce from
grouping entirely; fixing the corpus's actual jurisdikce values was
sufficient. Checked the real corpus for the 3 unique bare designations
found in §8's sizing pass (`EN 17127`, `ISO 14687`, `EN 17339`): the
first two already had both sides present (just wrong/missing jurisdikce
and an unresolved ČSN-side title); only `EN 17339` genuinely needed a
brand-new `ČSN EN 17339` record synthesized from scratch (confirmed live
to be a real, valid, currently-registered standard with no prior record
of its own anywhere in this corpus). Deliberately **out of scope**:
retroactively synthesizing an international-original row for the ~30
*other* ČSN-prefixed designations in the corpus that have no
international sibling today — the user's instruction was about records
already citing the bare form, not a systemic rewrite.

**Two real bugs found and fixed only by actually running the full
pipeline, not just unit tests**:
- `deduplicate_db.py`'s `programmatic_merge()` picks its base record by
  longest `nazev_cz` — not necessarily the cluster member that actually
  resolved an authoritative hit. Found live: `ČSN ISO 19880-1` (the
  correctly-spelled Prokop_Normy row, with a resolved title/URL) and
  `ČSN EN ISO 19880-1` (the spurious-EN Haltuf_Dokumenty rows, longer
  `nazev_cz`, no resolved title) share a dedup cluster; the merge kept
  the longer-titled member and silently dropped the resolved
  `nazev_autoritativni`/`zdroj_autoritativni_url`/etc. entirely. Fixed by
  adding these fields to the merge's existing backfill-from-any-member
  list (same fix automatically covers `resolve_iso_csn_ambiguity()`,
  which reuses the same merge function).
- A same-run cache-key clobber: several raw rows can share the exact
  same `"csn:<znacka>"` cache key (repeated citations of the same
  designation across a source); with `--force`, reprocessing the same
  key more than once per run let a LATER duplicate's write silently
  overwrite an EARLIER iteration's `synthesize` block for that same key.
  Fixed by tracking keys already handled this run and skipping repeats,
  regardless of `--force` (which still means "ignore the disk cache from
  a *previous* run," not "reprocess a key already done this run").
- A related bootstrapping bug, found on a second full rebuild: gating
  the `synthesize` block on "does this designation already exist in
  `database_merged_raw.json`" is circular — that file is rebuilt from
  scratch by `build_unified_db.py` every run and never natively contains
  a synthesized record (only the synthesize mechanism itself adds one),
  so after the FIRST successful synthesis, a later `--force` re-fetch
  would see the designation as "already there" and stop proposing the
  `synthesize` block — silently losing the record on the next
  from-scratch rebuild. Fixed by making `fetch_authoritative_metadata.py`
  always propose the block and letting `build_unified_db.py`'s own
  check against its FRESH `unified_db` (rebuilt from the 6 real sources
  every run, so never circular) be the sole gatekeeper.

**Verified end-to-end** (2026-09-13): 455 ČSN lookup attempts, 125 with a
real title (many of the rest are genuine ISO committee-draft/work-item
stages — `ISO/AWI`, `ISO/CD`, `ISO/DIS`, `ISO/PWI`, `ISO/WD` — that
correctly have no Czech adoption yet, not a failure). 7 new
`ČSN_Adoption_AgenturaCAS`-sourced records added. `document_relations_auto.json`'s
R1.4 `ADOPTS` edge count rose from 15 to 25, covering all three §8 target
designations (`EN 17127`, `ISO 14687`, `EN 17339`) automatically, with no
changes to the linking script. **Zero** `Document.url` rows still point
at `technicke-normy-csn.cz` (down from 34) — every one either resolved to
a real `agentura-cas.cz` URL or, where no confirmed match exists,
correctly kept its original citation. `resolve_url()` (new, mirrors
`resolve_title()`/`resolve_description()`) makes this the actual link
`app/templates/index.html` renders as "go to source" — spot-checked live
against 3 resolved catalog numbers (522022, 521108, 510858), all match
exactly. `needs_review` rose from 402 to 409 (the 7 synthesized records
have no description yet, correctly flagged, not silently exempted). Full
428-test suite passes; full pipeline rerun clean.

## 10. Footer metadata: DB last-updated + running app's git version (NEW, 2026-09-13)

Small, user-requested addition, unrelated to §9 above: `app/app.py` gained
`get_db_last_updated()` (`SELECT MAX(updated_at) FROM Document` —
`Document.updated_at` is already `ON UPDATE CURRENT_TIMESTAMP`, so no new
tracking was needed) and `get_git_version()` (`git describe --tags
--always --dirty` against `REPO_ROOT`, computed once at import time,
never raises — a deployment without git installed or without `.git/`
just shows nothing). Both are injected into every template via a new
`@app.context_processor`, and rendered in `base.html`'s footer as a small
muted line below the existing copyright text. Verified live against the
Flask dev server (not just the unit tests) — both values render
correctly. 6 new tests in `tests/test_app_export.py`.

## 11. `Sinay_Zakony`'s `DocumentType` was hardcoded to "Zákon" for every record (NEW, 2026-09-14)

User-reported: filtering/browsing by document type "Zákon" (Act) turned up
EU Regulations, an EU Directive, and Slovak/Czech Vyhlášky ("Vyhláška MV
SR č. 699/2004", "Vyhláška č. 94/2004 Z. z.", ...) — not Acts at all.
Root cause confirmed in `build_unified_db.py`: the `Sinay_Zakony` source
(the CZ/SK/EU law-mapping spreadsheet) unconditionally stamped
`typ_dokumentu: "Zákon"` on every one of its 48 raw records, regardless
of what the record's own title actually said it was — this source mixes
real Acts with Vyhlášky, Nařízení vlády (government regulations), and EU
acts cited as a Czech law's own EU counterpart (via its `Dokument EU`
column, which — for a record with no separate CZ/SK equivalent — becomes
this record's *only* title text, e.g. "Nařízení Evropského parlamentu a
Rady (EU) 2019/2144").

**Fix**: new `classify_sinay_zakony_typ(nazev)` in `build_unified_db.py`,
using the same leading-word legal-drafting convention already followed
by `resolve_prokop_jurisdikce()`'s bare-designation checks — Czech/
Slovak legislation reliably names its own type as the title's first word
("Zákon", "Vyhláška", "Nařízení vlády"), and an EU institutional act is
recognized either by an explicit `"(EU)"`/`"(EÚ)"` marker or a named EU
institution ("Evropského parlamentu"/"Evropské rady"/"Komise") — checked
against the real 48-record corpus to confirm this never triggers on a
genuine national Zákon/Vyhláška/Nařízení vlády title. Two records are
genuinely unclassifiable and correctly fall through to `""` (→ `init_db.
py`'s existing `FALLBACK_DOCUMENT_TYPE` = "Nezařazeno", reused rather
than duplicated): a "Vodíková stratégia..." policy strategy paper (not a
binding instrument at all) and "(EHK OSN) č. 134" (a UN/ECE vehicle
regulation — a real international instrument, but not any of the Czech/
Slovak/EU categories this classifier knows).

**Verified on the real corpus**: before the fix, all 48 `Sinay_Zakony`
records → `Zákon`. After: `Zákon` 26, `Nařízení EU` 9, `Vyhláška` 6,
`Nezařazeno` 2, `Směrnice EU` 2, `Nařízení vlády` 2, `Rozhodnutí EU` 1 —
and post-dedup/import, `DocumentType.name = 'Zákon'` now holds exactly
17 records, every one a genuine Czech Act (`100/2001 Sb.`, `458/2000
Sb.`, `262/2006 Sb.` "zákoník práce", ...), and the four Slovak decrees
the user named (`699/2004`, `94/2004`, `96/2004`, `124/2000 Z. z.`) now
correctly show `type_name: Vyhláška`. Full test suite (437 tests) passes;
full pipeline rerun clean.

## 12. Small UI tweaks (NEW, 2026-09-14, user-requested)

- `app/app.py`'s dev-server default port changed 5000 → 5050 (matches
  what's actually been used to verify this app all session).
- `app/templates/index.html`: each row's expanded detail now shows
  "ID záznamu: {{ doc.id }}" (small, muted — `.record-id` in
  `app/static/style.css`) under "Platnost od", so a user reporting a
  data error can name the exact record.
- `app/static/style.css`: `.action-block`'s "Přejít na zdroj"/"Stažená
  kopie" buttons used to right-align at their own, different natural
  widths (`align-items: flex-end`, no `gap`) — changed to `align-items:
  stretch` (both share the wider button's width, matching
  `.action-group`'s already-existing export-button row) plus `gap:
  0.5rem` (same value `.action-group`/`.filter-group` already use). The
  block itself stays `width: fit-content; margin-left: auto` so it still
  hugs the right edge rather than stretching across the whole grid cell;
  the ≤992px mobile override resets that back to `width: auto` (full
  single-column width, still equal-width buttons).

## 13. `(EHK OSN) č. 134` (Document id 87): manual correction of a specific bad record (NEW, 2026-09-14, user-reported)

User spotted `id=87`'s title was literally its own citation number,
`"(EHK OSN) č. 134"` — "looks very suspicious, crosscheck the whole
record." Root cause: the `Sinay_Zakony` source spreadsheet gives this
record NO real title at all (both `Dokument CZ`/`Dokument SK` are just
the bare citation), so it fell straight through to the raw-citation
fallback. Its `anotace_poznamka` (a vague, partly-wrong paragraph
mentioning vehicle "emisí" — this regulation has nothing to do with
emissions) was clearly LLM-generated at some earlier point with nothing
but the bare citation as input (all 47 *other* `Sinay_Zakony` records
carry similar-looking annotations, but had real title text to work
from — this is the one where the input was empty, and it shows).

**Verified independently, twice**: this is UN/ECE Regulation No. 134
(hydrogen-fuelled vehicle safety), incorporated into EU law as CELEX
`42019X0795` (OJ L 129, 17.5.2019) — confirmed both via `WebFetch`
against the real `eur-lex.europa.eu` Czech-language page and,
separately, by querying `src/sites/eurlex.py`'s own Cellar SPARQL for
that CELEX directly (same title both times): *"Předpis Evropské
hospodářské komise Organizace spojených národů (EHK OSN) č. 134 –
Jednotná ustanovení pro schvalování motorových vozidel a jejich
konstrukčních částí z hlediska bezpečnosti vozidel na vodíkový pohon
(HFCV) [2019/795]"*.

**Fixed**:
- `data/site_metadata_cache.json`: added a manually-verified entry keyed
  by the record's own `odkaz_sk` (`slov-lex.sk/.../ZZZ/2006/134/`, live-
  confirmed to be a dead link — a redirect-failure page, not real content;
  `fetch_authoritative_metadata.py`'s `slovlex` module correctly recorded
  it as `"failed"`, since there was no automatic way to find the right
  source from this URL alone) — carries the verified title and the
  working `zdroj_autoritativni_url` (the EUR-Lex CS "ALL" page —
  `https://eur-lex.europa.eu/legal-content/CS/ALL/?uri=CELEX:42019X0795`,
  the user's own pick over the "TXT" variant first used). **Known risk,
  documented rather than engineered around**: an `--force` re-run of
  `fetch_authoritative_metadata.py` will re-dispatch this URL to the
  `slovlex` module, get `"failed"` again, and silently overwrite this
  manual entry — a rare, deliberate operation, not something to add
  cross-record protection machinery for one record.
- The stale `anotace_poznamka` was hand-cleared (not merely overlaid —
  `popis_autoritativni` only ever *adds*, never suppresses a bad
  `anotace_poznamka`) directly in the generated `database_merged_raw.json`
  after one `build_unified_db.py` run, breaking `load_previous_
  annotations()`'s restore chain for this one record going forward (same
  precedent as this project's other hand-curated corrections, e.g.
  `sinay_normy_processed.json`).
- `data/fulltext_manifest.json`: the cached "full text" file was, itself,
  the same slov-lex redirect-failure page (real `HTTP 200`, but the body
  is an error page — `fetch_fulltext.py` had no way to detect this from
  the status code alone). Marked `"status": "failed"` with an `"error"`
  note; the useless cached file deleted. Without this, the app would have
  offered a "Stažená kopie" button serving a useless error page.

**Verified live in the running app**: `id=87` now shows the real title,
links to the working EUR-Lex page, has no fake download button, and is
honestly flagged "Vyžaduje kontrolu" (`chybí popis/anotace dokumentu`) —
no fabricated description was written to replace the bad one.

**Found while cross-checking, left as-is per the user's call**: `id=87`
is a genuine, pre-existing duplicate of `id=132` (`Haltuf_Dokumenty`,
`znacka="[2019/795]"`) — the *same* UN/ECE Regulation 134, already
correctly resolved via the normal `eurlex.py` SPARQL path (its own
`odkaz_hlavni` is a proper `eur-lex.europa.eu?uri=CELEX:...` URL) to the
identical Czech title, with a real working PDF `file_path`, `gestor`,
and English `language`. `deduplicate_db.py` never had a chance to catch
this: before today's fix the two records' titles looked completely
unrelated (`"(EHK OSN) č. 134"` vs the full English regulation title),
and their `znacka` share no common substring either. Shown side-by-side
to the user; their instruction was to correct `id=87` directly (using
the EUR-Lex "ALL" URL above), not to merge — `id=132` is left
untouched, and the two remain separate `Document` rows. Not a systemic
fix (only this one pair was checked) — a broader duplicate-detection
pass across the corpus, if wanted, would be separately scoped work.

## 14. `DocumentType` correctness audit — `Haltuf_Dokumenty`'s own `typ_dokumentu` was never classified at all (NEW, 2026-09-15, user-reported)

Follow-up to §11: the user spotted several more misclassified records in
the default view (`id=96/97/100` should be `Směrnice EU`/`Nařízení EU`,
`id=109/147` `Nařízení vlády`, `id=67/108` `Zákon`, `id=139` `Vyhláška`)
and asked for a full "typ" correctness audit, focused on `Nezařazeno`.
**Note for future sessions**: `Document.id` is NOT stable across a
pipeline rerun (`init_db.py` `TRUNCATE`s and reinserts every run, so ids
are reassigned by processing order) — most of the user's cited ids still
matched live at investigation time, but one (`id=147`) had already
drifted to an unrelated `Norma` record from an earlier fix's rebuild.
Investigated by title/znacka, not by chasing stale id numbers.

**Root cause, much broader than the cited examples**: `Haltuf_Dokumenty`
sets `"typ_dokumentu": item.get("Typ_ID", "").strip()` — a **raw,
uninterpreted numeric category id** straight from the spreadsheet ("1",
"2", "9", "10", ...), never translated into a real `DocumentType` name.
Checked: **all 179 of 179 raw `Haltuf_Dokumenty` records** had a blank or
purely-numeric `typ_dokumentu`, so every one fell to `init_db.py`'s
`FALLBACK_DOCUMENT_TYPE` ("Nezařazeno") on import, unless it happened to
dedup-merge with a correctly-typed `Sinay_Zakony`/`Prokop_Normy`/
`Sinay_Normy` sibling row citing the same document — and even that safety
net was unreliable: `deduplicate_db.py`'s `programmatic_merge()` copies
`typ_dokumentu` from whichever cluster member has the *longest*
`nazev_cz`, with no notion of "prefer a real classification over numeric
junk" — a genuine bug found live (`201/2012 Sb.` has both a
correctly-`"Zákon"`-classified `Sinay_Zakony` row and a numeric-junk
`Haltuf_Dokumenty` row; the Haltuf one, longer, won the merge and
silently overwrote the correct type). Mapping the numeric ids to real
category names (a lookup table) was considered and rejected: no such
table exists anywhere in the pipeline, and it would be an indirect,
harder-to-verify proxy for what's already reliably readable straight
from the record's own title text — the same "first word states the
type" legal-drafting convention already exploited for §11.

**Fixed**: `classify_sinay_zakony_typ()` generalized to
`classify_law_document_typ()` and reused for **both** sources (was
Sinay_Zakony-only), broadened to also correctly classify:
- **A compound-noun `Zákon` form** ("Energetický zákon", "Stavební
  zákon", "novela Zákona o drahách") — Haltuf frequently names a
  well-known Act this way, not "Zákon č. ... Sb." — so `_ZAKON_RE` is no
  longer anchored to the start of the title, only Vyhláška/Nařízení
  vlády still are (verified: broadening this specific check doesn't
  trigger on any genuine EU-act title in either corpus — none mention
  "zákon" in their own designation text at all).
- **English-language EU act titles** — Haltuf carries a parallel English
  row for most EU acts ("DIRECTIVE OF THE EUROPEAN PARLIAMENT...",
  "COMMISSION REGULATION...", "DECISION OF THE EUROPEAN CENTRAL
  BANK...") — added `directive`/`regulation`/`decision` and `European
  Parliament`/`Council`/`Commission`/`European Central Bank` (also in
  Czech: "Evropské centrální banky") as recognized institution/type
  markers alongside the existing Czech/Slovak/`"(EU)"`/`"(EÚ)"` ones.
- **A second real bug, found only by running this against the full
  corpus rather than a handful of hand-picked cases**: matching by fixed
  check priority (Směrnice, then Rozhodnutí, then Nařízení) misclassifies
  an act that states its own type up front but *also* cites a different
  act of a different type later in its own title (amending/repealing
  clauses are common in EU legislative titles) — e.g. `(EU) 2023/1804`
  is itself a **Nařízení** that repeals a directive
  ("... a o zrušení směrnice 2014/94/EU"), and `(EU) 2024/1789` is a
  **Nařízení** that also cites a Decision and repeals another Nařízení.
  Fixed by matching on **earliest keyword position** in the text instead
  of a fixed priority order.
- **Bare norm designations** embedded among Haltuf's law citations
  ("ČSN EN 17127", "EN 17339", "DIN EN ISO 22734", ...) now classify as
  `"Norma"` (same designation-prefix shape as `fetch_fulltext.py`'s own
  `is_norm_designation()`) instead of `"Nezařazeno"`.
- Genuinely non-EU international instruments (ADR, RID, UN/ECE
  regulations like `(EHK OSN) č. 134`/`"UNECE Regulation No. 100"`) — and
  a Commission *Communication* (policy paper, not a binding type)
  — correctly stay unclassified: verified they cite "Regulation"/
  "Agreement" too, but with no EU/CZ/SK institution attached, so the
  EU-institution gate never opens and the national-prefix checks don't
  match either.

**Verified end-to-end on the real corpus**: `Nezařazeno` dropped from
(effectively) all ~226 combined `Sinay_Zakony`+`Haltuf_Dokumenty` records
down to **6**, every one individually confirmed genuinely unclassifiable
(the Communication, `(EHK OSN) č. 134`, ADR 2025, RID ×2, UNECE R100) —
none silently force-guessed. All of the user's cited examples now show
the correct type (`Zákon` 26, `Nařízení EU` 26, `Směrnice EU` 13,
`Vyhláška` 8, `Nařízení vlády` 5, `Rozhodnutí EU` 3 — plus `Norma` rising
by the newly-recognized bare Haltuf norm citations). No change needed to
`deduplicate_db.py`'s merge logic itself: once every raw record is
correctly classified (or genuinely empty) *before* merge, the existing
backfill-from-any-member logic resolves multi-row records correctly on
its own. 448-test suite passes; full pipeline rerun clean.

## 15. Source-agnostic schema pivot: split multi-jurisdiction records + superset audit fields (NEW, 2026-09-15, user-directed)

Tagged commit `heterogeneous_version` marks the last state built on the
per-source model (`zdroj_dat`: which of the three original spreadsheets —
Prokop/Sinay/Haltuf — a record came from). The user's explicit direction:
those spreadsheets were only ever "seeds" to establish the legal corpus —
every pipeline operation from here on should treat every `Document` as a
homogeneous element, not branch on its origin. The schema should hold
whatever superset of properties the sources actually provide, instead of
quietly dropping what doesn't fit today's narrower `Document` table.

**A full-repo audit (not assumed) found most of the pipeline already
source-agnostic**: `app/app.py` has zero `zdroj_dat` references;
`deduplicate_db.py`/`link_document_versions.py` only ever concatenate it
into a provenance string; `link_document_relations_auto.py` was already
deliberately keyed on `znacka` shape, not source. Only two real
behavior-branches remained: `fetch_authoritative_metadata.py`'s
`LAW_SOURCES`/`CSN_ELIGIBLE_SOURCES` and `fetch_fulltext.py`'s
`NORM_SOURCES` — both switched to a `typ_dokumentu`-based check instead
(`!= "Norma"` for law-record gating, `== "Norma"` for the norm-only
gates), now that §11/§14 made `typ_dokumentu` reliably real for every
source. `doc/REQUIREMENTS.md` R1.6's "independent classification table"
is unrelated — it's about the document's authoritative *institution*
(`DocumentSource`, from `gestor`), not which spreadsheet it came from.

**First plan draft rejected by the user.** The initial proposal folded
`nazev_eu`/`nazev_sk`/`odkaz_eu`/`odkaz_sk` into extra columns on one
`Document` row. Rejected: the EU version of a law is the legally binding
original; CZ/SK versions are national implementations *derived from
it* — these must be **separate, interlinked `Document` rows**, the same
"split, don't bundle" pattern already used for international-standard↔
ČSN-adoption (§9's `ADOPTS`). Revised design: reuse the existing
`IMPLEMENTS` relation for EU→national (same real-world relationship
R1.3 already models); add a new `NATIONAL_EQUIVALENT` relation type for
CZ↔SK pairs with no EU parent; no leftover "non-authoritative URL"
field survives the split — each split-out record just gets the ordinary
`url`.

**Schema additions** (`doc/konsolidace/Konsolidace-DB-schema.sql`,
applied live): `document_relation.relation_type` ENUM gains
`NATIONAL_EQUIVALENT`; `Document` gains five nullable audit/provenance
columns that survive as themselves (not split into rows) —
`zdroj_dat` (comma-joined provenance, never branched on), `nazev_
autoritativni`/`popis_autoritativni`/`zdroj_autoritativni_url` (the
independently-verified fields, kept alongside `title`/`description`/
`url` so "is this verified?" stays answerable after they've won), and
`jurisdikce_puvodni` (§9's pre-correction jurisdikce audit trail).
Deliberately excluded: `ratifikovan` — checked across all 2248
pre-pivot raw records, exactly **one** non-blank value exists anywhere
(`"A=ANO; N=NE"`, a legend fragment leaked into the data column by a
`process_haltuf.py` extraction bug, not real data) — adding it now would
surface garbage into a "superset" schema; needs its own root-cause fix
first, out of scope here.

**`build_unified_db.py`'s new `split_sinay_zakony_row()`** splits one
Sinay_Zakony spreadsheet row into up to 3 records instead of one row
with 6 title/url fields: a primary (CZ if present else SK, same
fallback as before, now with `jurisdikce` set explicitly — previously
left blank for this whole source), an SK sibling when "Dokument SK" is
genuinely distinct dual content, and an EU original whenever "Dokument
EU" is populated. `nazev_eu`/`odkaz_eu` stay on the primary record in
the intermediate JSON (unchanged) so `link_document_relations_auto.py`'s
existing R1.3 mechanism can still find and link the now-real EU record —
**zero changes needed to that script**. The CZ↔SK pairing (nothing
downstream can recover it later — Czech and Slovak laws don't share a
common znacka/digit-core the way an EU-act citation does) is captured at
build time into a new `data/document_relations_split.json`, merged by
`load_document_relations.py` as a third source alongside the existing
hand-curated and auto-detected ones.

**Real pre-existing bug fixed as a side effect**: `odkaz_hlavni` used to
always read `"URL CZ"`, even on a row where the title itself fell back
to `"Dokument SK"` because `"Dokument CZ"` was blank — 9/48 real rows
ended up with a blank `odkaz_hlavni` despite a perfectly good `"URL SK"`
being available.

**Three more real bugs found live, only by actually running the split
against the full corpus and the database, not by unit tests alone**:

1. **A Slovak-spelled EU citation collided with the same act's
   correctly-spelled record, but only inside MariaDB.** `extract_znacka_
   from_title()`'s leading-match cases (B) never normalized the Slovak
   "EÚ" spelling to "EU" (only the anywhere-in-text case F did) — two
   Python strings `"(EÚ) 2019/2144"` and `"(EU) 2019/2144"` are distinct
   to `init_db.py`'s own-run duplicate check, but MariaDB's
   accent-insensitive collation treats them as the same `identifier`,
   crashing the `INSERT` with a unique-constraint violation. Fixed:
   case B now also normalizes `EÚ`→`EU` (deliberately **not** `ES`→`EU`
   there — `"1999/92/ES"`, the pre-Lisbon designation, is kept literal
   by an existing, still-passing test; only the accent difference was
   ever the bug).
2. **A bare EU citation copy-pasted into "Dokument SK" isn't real
   Slovak content.** 2/48 rows have `"Dokument SK"` holding nothing but
   the EU act's own citation (e.g. `"(EÚ) 2019/2144"`) instead of an
   actual Slovak-language title — splitting it out would create a
   content-free "document" that's really just the EU original under a
   different jurisdikce. Detected via `extract_znacka_from_title(sk) ==
   sk` (the whole cell is consumed by the citation regex, nothing else)
   and skipped.
3. **EU Regulations (unlike Directives) apply directly — there is no
   separate national implementing act — but Sinay's spreadsheet still
   fills "Dokument CZ"/"Dokument SK" with a copy of the same
   regulation's own title for these rows.** 10/48 rows (e.g. `"(EU)
   2023/1184"`, `"(EU) 2019/2144"`) have this shape, confirmed by their
   own extracted znacka matching `"Dokument EU"`'s. Splitting these
   produced 2-3 records sharing the *exact same* znacka under different
   jurisdikce, which then (a) collided as duplicate identifiers in
   `init_db.py` and, worse, (b) made `link_document_relations_auto.py`'s
   R1.4 grouping treat the EU-tier copy as "parent" and the CZ/SK-tier
   copy of the *same* citation as "child", emitting a literal
   **self-referencing `X ADOPTS X` edge** — which crashed
   `load_document_relations.py`'s insert on `document_relation`'s
   unique constraint. Fixed at the root: when a row's primary record and
   its EU original resolve to the same znacka, collapse to a **single**
   EU-tier record instead of splitting. Also added a general defensive
   guard in `find_localization_pairs()` (never link a record to itself
   via a shared znacka) — this caught one more, unrelated self-loop
   (`"2010/75/EU"`) rooted in `extract_znacka_from_title()`'s
   anywhere-in-prose case picking up a *cited* directive's number from a
   Commission Decision's own title, not the Decision's own designation —
   a separate, pre-existing extraction imprecision, out of scope to fix
   generally here, just guarded against.

**A fourth issue, structural rather than a single bug**:
`document_relations_split.json` is written per raw spreadsheet row,
before `deduplicate_db.py` merges duplicate rows into one final
`Document` — the same CZ+SK pair can legitimately appear on more than
one raw row, resolving to an identical `(from_document_id,
to_document_id, relation_type)` triple twice. `load_document_relations.py`
gained a general `dedupe_resolved_relations()` pass (applied to
resolved relations from *any* source, not just the split one) right
before the insert loop.

**`init_db.py`**: `import_json_data()`'s `INSERT INTO Document` extended
with the five new columns, direct pass-through (no resolution logic
needed — they're audit companions to the already-resolved `title`/
`description`/`url`/`jurisdikce`).

**Verified end-to-end on the real corpus** (full pipeline rerun:
`build_unified_db.py` → `deduplicate_db.py` → `link_document_
versions.py` → `link_document_relations_auto.py` → `init_db.py` →
`load_document_relations.py` → `load_process_layer.py`; 467-test suite
passes):
- Raw unified records: 2248 → 2280 (Sinay_Zakony alone: 48 source rows →
  80 records — CZ 29, SK 35, EU 16; 10 of the 48 rows collapsed to a
  single EU-tier record per bug #3 above, not tripled).
- Deduplicated records: 1191 → 1215 (1238 live `Document` rows including
  the pre-existing +23 V02-bibliography placeholders `load_process_
  layer.py` adds, unrelated to this pivot).
- R1.3 `IMPLEMENTS` edges: 0 (6 candidates stuck in `eu_transposition_
  missing_targets.json`, missing their target) → **6 edges, 0 missing**
  — the fix was entirely upstream of `link_document_relations_auto.py`
  (making the cited EU act a real record); the script itself needed zero
  changes, exactly as designed.
- `document_relation` total: 46 rows (`AMENDS` 1, `IMPLEMENTS` 6,
  `ADOPTS` 25, `NATIONAL_EQUIVALENT` 14 — 18 split-detected pairs minus 4
  exact-duplicate triples dropped by the new dedupe pass).
- Spot-checked real triples, e.g. `458/2000 Sb.` (CZ) `IMPLEMENTS`
  `(EU) 2019/692` (EU, now a real linked record instead of a string on
  the CZ row); `183/2006 Sb.` (CZ) `NATIONAL_EQUIVALENT` with two
  distinct Slovak successor laws from the same source row.
- `fetch_authoritative_metadata.py`/`fetch_fulltext.py` gating reaches
  the same *kind* of records as before (219 law records / 421 ČSN-
  eligible / 317 full-text fetch targets on the fresh corpus), now via
  `typ_dokumentu` instead of `zdroj_dat`.

**Manually browsed a real CZ/SK/EU triple in the running Flask app**
(no UI template changes needed or made — §7 correctly predicted the
split records "show up as ordinary searchable `Document` rows already"):
`458/2000 Sb.` (id=90, CZ, `Zákon`, links to its e-Sbírka page) is
`NATIONAL_EQUIVALENT` to `250/2012 Z. z.` (id=91, SK, `Zákon`, links to
slov-lex.sk) and `IMPLEMENTS` `(EU) 2019/692` (id=103, EU, `Směrnice
EU`, links to eur-lex.europa.eu) — three separate, correctly-tagged,
correctly-linked search results instead of one row with 6 bundled
title/url fields. The SK sibling correctly shows a `needs_review` flag
(no `anotace_poznamka` of its own, expected for a split-out record) and
inherits the primary's `gestor`-derived source list, as designed.

## 16. Language, norm designation, Gestor semantics, stable slug, pagination + document page (NEW, 2026-09-15/16, user-reported)

Two sessions' worth of user-reported findings, recorded together because
each one exposed the next. Commit `c5d40d6` (2026-09-15) shipped the
first three items below **without a PLAN entry** — and left three
dangling `doc/PLAN.md §16` references in `src/sites/eurlex.py` and
`src/sites/0README.md` pointing at a section that did not exist. This
section retires those references.

### 16.1 Language indicator missing for 94 % of the corpus (2026-09-15)

**User finding:** the language badge showed for only some documents.
Reality: 1163 of 1238 records had `language` blank or NULL — only ~75
carried a value, and those were spelled four different ways (`"CZ"`,
`"čeština"`, `"angličtina"`, `"EN"`). The user asked for EN/CS/SK/DE
designations on all of them.

New `src/tools/language.py` + `backfill_language.py`:
`normalize_raw_language()` maps the known raw spellings (note `"CZ"` →
`CS`: `CZ` is a country code, not a language code), and
`detect_language()` handles the rest via `langdetect`
(`DetectorFactory.seed = 0`, so it is deterministic), restricted to the
four languages the corpus actually contains.

**Real bug found and fixed during the work.** The first implementation
detected over `title + " " + description`. That confidently
(`prob > 0.85`) labelled **217 of the 424 `jurisdikce="SK"` records as
`DE`** — because a large number of records carry a scope/abstract in a
*different* language than the document itself (a Slovak-titled standard
whose stored description is the German-language scope text of the
underlying EN norm), and the long description simply outweighs the short
title. Fixed by detecting from the **title alone**, with the description
used only as a fallback when the title is empty or inconclusive, never
to override a confident title result. Verified on the real corpus:
417/424 of that subset then resolved to `SK`.

Result: 1218/1238 rows updated (55 raw-value normalisations, 1108
confident detections, 55 low-confidence ones flagged through the
existing `needs_review` mechanism rather than silently asserted), **0
documents left without a language**. Final distribution EN 529 / SK 436
/ DE 148 / CS 125.

### 16.2 Norm titles never showed their own designation (2026-09-15)

**User finding:** many norms "do not bear identification number ... or do
bear the number at the end of the title (it shall be at the beginning)".

Root cause: `app/app.py` had never queried or displayed
`Document.identifier` at all. The only thing the catalogue ever showed
was `title`, which for essentially every `Norma` record is plain
descriptive prose with no designation — while a handful of Sinay records
*did* carry it, but embedded as a trailing `"(DESIGNATION:YYYY)"`
parenthetical.

New `src/tools/norm_title.py` + `backfill_norm_designation.py` normalise
both shapes into `"<designation> — <title>"`. 1078 of 1104 `Norma`
titles were prefixed; 26 were left untouched because they genuinely have
no designation (German `BVEG`/`AGBF` industry guidance leaflets, each
one checked by hand). Side effect worth knowing: since the list is
sorted by `title`, the default browse order is now grouped by
designation prefix.

Two follow-up defects in `designation_core()` were found on 2026-09-16
while deriving slugs from the same function, and both had already
written wrong titles into the database:

* The edition-suffix stripper matched **any** trailing `-NNNN`, so a
  designation whose own number sits after a dash lost it — `"ZP-5101"`
  became `"ZP"`, `"SAND2012-7321"` became `"SAND2012"`. Restricted to
  plausible years (`19xx`/`20xx`), which still strips the real artifact
  *and* the bare `-YYYY` edition suffix US/Australian designations
  legitimately carry (`"ASME B31.12-2019"`, `"AS 2022-1983"` — verified
  against all 509 identifiers the pattern fires on). 3 titles repaired.
* The separator had to be an ASCII `-`, but the Sinay source mixes in
  en-dashes (`"STN EN 13365/A1 – 2003.08"`), so **17 records kept their
  edition date inside the designation, and therefore inside the title**.
  Same class of defect as the dash-continuation bug `parse_sinay_norms.py`
  had to fix in §7. 17 titles repaired.

Both repairs recomputed the title from the untouched source JSON rather
than re-running the backfill over the already-wrong stored value, which
would have double-prefixed. `backfill_norm_designation.py` also had a
reporting flaw — it counted "has a designation" as "changed", so it
always claimed 1078 updates even when every recomputed title was
byte-identical; it now reports genuine differences only.

### 16.3 "Gestor" (renamed from "Původce") must be ONE institution (2026-09-15/16)

**User finding:** the field "shall be a single institution issuing the
given document, but very often we have a list of them that seems to be
hardcoded."

Root cause: `init_db.py` wrote `source = ", ".join(gestor)` — the whole
raw list, including AI-generated (`enrich_eu_laws.py`) entries that are
themselves multi-line blobs (a Directorate-General list plus free-text
commentary). 26 of 41 `DocumentSource` rows were such concatenations.

The semantics needed a user decision, because "gestor" (the ministry
with substantive responsibility, legitimately plural under Czech joint-
gestor practice) and "issuer" (the body that enacted the document, always
singular) are different concepts. **User decision (2026-09-15): keep the
"primary responsible ministry" concept, reduced to one institution.**
New `src/tools/puvodce.py` + `backfill_puvodce.py`: take the first clean
entry of the list, and canonicalise bare abbreviations so `"MPO"` and
`"Ministerstvo průmyslu a obchodu"` stop being two different rows.
(`"MZ"` → `Ministerstvo zdravotnictví` was verified from the record that
uses it — an act on public-health protection — not guessed from the
abbreviation, since `Ministerstvo zemědělství` was already present and
would have been the wrong expansion.) 41 → 12 clean rows.

**Then the user asked to check ids 98 and 101 specifically.** Those two
turned out fine (an official government legislative-plan source confirms
MPO as lead gestor for RED III), but checking them surfaced a structural
problem: across the EU-act types, Gestor arbitrarily showed *either* a
Czech ministry *or* an EU institution, purely according to which happened
to come first in each record's AI-generated list. **User decision
(2026-09-16): for an EU act the Gestor is the EU body — the specific
Directorate-General when available, else the top-level institution — and
it must come from the authoritative source, not from the erratic local
data.**

`src/sites/eurlex.py` gained `fetch_responsible_gestor()`, querying the
EUR-Lex/Cellar SPARQL endpoint for `cdm:resource_legal_responsibility_of_agent`
(the DG Cellar itself calls "responsible"), falling back to
`cdm:work_created_by_agent`, with Czech names resolved via
`skos:prefLabel`. Matching is done through `owl:sameAs` on whichever URL
shape the record already has (CELEX / ELI / bare `OJ:` reference), which
sidesteps CELEX reconstruction entirely — EU act numbering flipped
order in 2015 (`No 402/2013` vs `2023/2405`), so rebuilding an id from a
designation alone is genuinely ambiguous. 43 of 44 EU acts resolved
(8 distinct DGs); results cached in `data/eu_gestor_cache.json`, which
`init_db.py` reads so a rebuild need not repeat ~44 live queries.

**`backfill_puvodce.py` had to be scoped down twice**, each time after
verifying the conflict live: once to exclude the EU act types (it
proposed reverting all 43 resolved records to a Czech ministry), and
again on 2026-09-16 to exclude `Norma` (it proposed reverting 5 ČSN
standards from `ČAS` back to `Ministerstvo průmyslu a obchodu`). The
three backfills now own disjoint slices — national acts (60), EU acts
(44), standards (1104) — and each is idempotent.

### 16.4 R1.6 regression from 16.3, and its repair (2026-09-16)

Collapsing the lists was right, but it left only **108 of 1238**
documents with any issuing body — **5 of 1104 standards** — and
`DocumentSource` contained no standard-setting body at all, which
`doc/REQUIREMENTS.md` R1.6 names explicitly. The requirements checker
could not see this because its R1.6 probe is `SELECT COUNT(*) FROM
DocumentSource` with no per-document coverage query.

No lookup was needed to fix it: **1080 `Norma` records carry their
publisher in the designation** that §16.2 had just moved to the front of
their titles. New `src/tools/standards_body.py` +
`backfill_standards_body.py` map the designation's first token to its
issuing body — curated by reading the actual records behind each token,
not assumed from the abbreviation. The cases that needed evidence:

* `G`/`GW`/`C`/`ZP`/`Gas-Information`/`G269` (102 records) are all DVGW —
  the titles cite the "DVGW-Regelwerk" and "DVGW-TRGI" directly and the
  whole family uses DVGW's own `(A)` Arbeitsblatt / `(M)` Merkblatt
  convention.
* `AS` is Standards Australia — the records' own titles say "known as
  the SAA Anhydrous Ammonia Code".
* `TNI` is the Slovak series, not the identically-named Czech one: all
  14 records carry `jurisdikce=SK` and Slovak titles.

Result: 1064/1104 standards resolved across 40 bodies; coverage
108/1238 (8.7 %) → **1167/1238 (94.3 %)**, `DocumentSource` 19 → 59
rows. The 40 left alone are 19 with no designation at all plus 21 whose
leading token this module deliberately does not recognise (`MB`, `SEP`,
`AR`, `TPP`, `TB.`, `PP`, `PAS`, the parse artefacts `Part`/`Band`/`A1`,
…) — left without a Gestor rather than guessed at.

### 16.5 The `(EU) 2018/546` record: a CELEX-suffix bug, not bad source data (2026-09-16)

While resolving EU gestors, one record (`(EU) 2018/546`) produced
"Generální sekretariát" and a title about **Danish state aid to Aarhus
airport** — an act with nothing to do with the corpus. It was initially
flagged as inconsistent source data. That diagnosis was wrong.

The source record is internally consistent: an **ECB** decision, with
`gestor: ['Evropská centrální banka']` and a matching `nazev_cz`. The
corruption was in `nazev_autoritativni`, written by §8's authoritative
fetch. Root cause, confirmed against Cellar: the correct CELEX for that
act **is** `32018D0010(01)` — the ECB numbers it ECB/2018/10, and
EUR-Lex uses the `(01)` suffix to separate it from the *Commission's*
decision 2018/10, which is the Aarhus one. `_CELEX_IN_URL_RE` captured
`(\w+)`, which stops at the parenthesis, so it silently resolved the
wrong act.

Fixed in `src/sites/eurlex.py` (the suffix is now part of the capture),
plus a new `eli_candidates_from_designation()` — Cellar does not index
this act under that CELEX at all, only under `eli/dec/2018/546/oj`.
With both fixes the record resolves to "Evropská centrální banka",
independently matching its own source `gestor` field. Repaired
upstream following §13's precedent — `site_metadata_cache.json` (2
entries), `data/eu_gestor_cache.json`, and both merged JSON files — not
only in the database, and the incorrect review flag was cleared.

This was a latent defect since §8 (2026-09-11), not something the recent
work introduced; only 1 record in the corpus currently has a
parenthesised CELEX. `(EU) 2023/1234` (id 105) remains genuinely
unresolvable — Cellar knows neither its CELEX nor its ELI — and is
flagged for review rather than guessed.

### 16.6 Stable `Document.slug` (2026-09-16)

§14 already recorded that `Document.id` is not stable across a rebuild
(`init_db.py` TRUNCATEs and reloads, so ids are reassigned by processing
order — an id the user cited, 147, had already drifted to an unrelated
record). That was tolerable while ids were only a label in the detail
accordion (§12), but §16.7's document page exists to be linked, so it
could not be keyed on one. **User decision: add a deterministic slug
column.**

`src/tools/slug.py` derives it from the designation
(`"ČSN EN 17124"` → `csn-en-17124`), falling back to a SHA-1 of the
title for the 64 records with no real designation. `assign_slugs()` is
deliberately a whole-corpus function: collision suffixes are handed out
in a content-derived order, never in input order, or two colliding
records would swap slugs between rebuilds and reintroduce exactly the
instability the column removes. 1238 unique slugs, only 2 real
collisions (both genuine duplicate pairs), and 0 records where the DB id
would break a tie. Additive `ALTER TABLE Document ADD COLUMN slug
VARCHAR(160) NULL UNIQUE`.

### 16.7 Pagination and the document page (2026-09-16)

`index()` passed a hardcoded `limit=100` with a static "showing the first
100" banner and no way to reach the rest, so **~92 % of the corpus was
unreachable through the UI**.

* Server-rendered pagination (`?page=N`, 50 per page, plain links — no
  JS framework, R3.4). The count query **must** be
  `COUNT(DISTINCT d.id)`: the keyword filter needs the `DocumentKeyword`
  join, which multiplies a document's rows by its keyword count, so a
  plain `COUNT(*)` would inflate the total and paginate into empty pages
  — the same R2.1 trap commit `ebc1f60` fixed once already. Verified
  live by walking all 25 pages: 1238 rows, no duplicates, count exact;
  and with the heaviest keyword (370 links) still exact. `/export/<fmt>`
  stays unpaginated.
* New `GET /dokument/<slug>` + `app/templates/document.html`, surfacing
  three things that were populated but had never appeared in the UI:
  **`DocumentVersion`** history (1258 rows, until now read only for the
  hero's aggregate count — this is what R1.5 was built for),
  **`document_relation`** (46 edges, rendered in both directions with
  correct phrasing from each end), and the record's jurisdiction
  columns. The CZ↔SK↔EU triple the user browsed by hand at the end of
  §15 is now navigable by clicking. R4.1's full-text gate is reused
  verbatim, and `/fulltext/<id>` keeps its independent server-side
  check.

### 16.8 Tests

The modules from `c5d40d6` shipped untested, and the full suite was
never run for that commit — it had in fact left **two failing tests** in
`tests/test_init_db.py` (`build_gestor_jurisdiction_map` was re-keyed to
the resolved institution but its tests still asserted the raw joined
string). Fixed, and the gap closed: new `tests/test_standards_body.py`,
`test_slug.py`, `test_language.py`, `test_norm_title.py`,
`test_puvodce.py`, plus extensions to `test_app_export.py` (pagination,
the `COUNT(DISTINCT)` guard) and `test_sites_eurlex.py` (multi-URL
fields, CELEX suffix, ELI candidates, DG-vs-institution selection).
467 → 580 tests, all passing.

## 17. Missing annotations, fetched from the sources rather than generated (NEW, 2026-09-16, user-directed)

**User direction:** *"The missing annotations shall be solved by directly
going to the document URLs and fetching theirs abstracts or summaries (or
synthesizing those in case that no abstract is available). The annotations
are written in Czech even for Slovak / German / English documents."*

458 of 1238 documents carry no description — 407 of them `Norma`.

### 17.1 Why not simply run `enrich_annotations.py`

Assessed before starting, and the answer was no. That script sends the
model only `Název` + `Typ`, and its own prompt instructs it to *"popiš
stručně, jakou oblast **obvykle** reguluje"* — family-level generalisation,
which is precisely the mechanism that produced §13's fabricated
"emissions" paragraph for a hydrogen-vehicle-safety regulation.

The decisive finding is upstream. The Sinay source
(`data/20250712_Sinay/sinay_normy_processed.json`) carries an `Anotace`
column, non-empty for **651 of 1942** rows, and `build_unified_db.py`
already copies it straight through — which is why **697 `Norma` records
in the live DB already hold authentic scope abstracts averaging 611
characters**. The 407 blanks are precisely the complement: the rows where
the source had no abstract. They are not a processing gap that generation
can close, and filling them from the title would place ~150-character
paraphrases indistinguishably beside genuine 611-character scope texts in
a regulatory reference database.

Hence the user's direction, and this section: **go to the source.**

### 17.2 The obstacle: there is no per-document URL to go to

Only **11 of the 407** store a real per-document URL, and those point at
`csnonline.agentura-cas.cz`, whose detail page publishes no abstract field
at all (`check_csn_validity.fetch_detail()` returns designation, title,
English title and "Zapracované dokumenty" — no scope). The other 396 store
a **catalog root**: `normy.normoff.gov.sk/` (101), `iso.org/standards.html`
(73), `dvgw.de/` (42), `webstore.iec.ch/` (17), `eiga.eu/` (16),
`bveg.de/` (14), and ~10 each for `din.de`/`ptb.de`/`csagroup.org`. 42 have
no URL at all.

So each domain needs a **designation → detail page** resolution step
first. That is the "search the site by designation" mechanism §8 deferred
as *"a substantially bigger, differently-shaped undertaking"*. It is being
built one domain at a time, highest-yield first, rather than as one push.

### 17.3 `src/sites/normoff.py` — the first domain (101 records)

The ÚNMS SR registry turned out to be well-suited: server-rendered (the
Slovak government IDSK design system, not a JS SPA), and it publishes a
**"Predmet normy"** scope field.

Two requests per designation, both cheap and deterministic:

1. `/vyhladavanie-export/?name=<designation>` returns a small CSV of every
   edition — catalogue number, title, issue date, **withdrawal date**,
   detail URL. Chosen deliberately over scraping the HTML result list: it
   is structured, stable, and the site offers it itself.
2. `/norma/<catalogue number>/` carries the scope text.

Edition choice reuses the rule `check_csn_validity.find_best_match()`
already applies to the Czech registry — prefer the edition still in force,
else the most recently issued. Here "in force" is an empty `Dátum
zrušenia`, i.e. a data field rather than a rendered label, so no HTML
parsing enters the decision.

**Three things found by testing against the live registry, each now
guarded:**

- **A naive extractor silently returned page chrome.** Reading "the line
  after the `Predmet normy:` label" in flattened text produced `"Hore"`
  (the back-to-top link) for records that have *no* scope — the registry
  leaves the cell empty rather than omitting the row. Fixed by parsing the
  actual table structure (`<td class="…title">label</td>` → following
  `<td>`), so an empty cell yields `None`. Left unguarded this would have
  written navigation text into ~25 % of the descriptions.
- **The corpus's own `znacka` carries Sinay's edition suffix**
  (`"STN EN 17339/ - 2025.02"`), which the registry matches against
  nothing. The first integrated run cached 4 straight failures before this
  was spotted; `designation_core()` (the same helper `norm_title.py` uses
  for titles and slugs) strips it.
- **Notation differences**: this corpus writes `"STN EN 16898 + A1"`, the
  registry `"STN EN 16898+A1"`. `designation_variants()` normalises the
  spacing — but deliberately does **not** fall back to the base standard
  when an amendment isn't found (`"STN EN ISO 11114-1/Zmena"` →
  `"STN EN ISO 11114-1"`), because the base is a *different document* and
  its scope would describe the wrong thing.

Only an EXACT designation match is accepted — the registry willingly
returns near misses for a partial designation. A bare `EN 12953-9` (not a
Slovak adoption) correctly resolves to nothing rather than to something
adjacent.

Measured on a 20-record spread of the 101: **13 with real scope text,
median 875 characters**, 5 resolved but with no scope published, 2
unresolved for the notation reasons since fixed.

### 17.4 Storage — fetched and synthesized are kept apart

Per the user's decision:

- **Fetched (and translated to Czech) → `popis_autoritativni`**, the
  existing "verified from the source" field, blank for all 458 today. This
  needs no new plumbing: `build_unified_db.apply_authoritative_metadata()`
  already re-applies it from `data/site_metadata_cache.json` on **every**
  rebuild, and `init_db.resolve_description()` already prefers it over
  `anotace_poznamka`.
- **Synthesized → a new `popis_priblizny`**, rendered with a
  **"Přibližné shrnutí, neověřeno"** marker and **keeping `needs_review`
  set**. It must never feed `Document.description`, or the distinction
  collapses and the database again cannot tell a reader which is which.

`fetch_authoritative_metadata.py` gained an `is_stn_norm_record()` branch,
keyed `stn:<designation>` — the same designation-keyed convention the ČSN
branch already uses (`csn:<znacka>`) for records with no per-document URL.
It is disjoint from the existing branches by construction: `is_csn_norm_record()`
matches a ČSN prefix or a bare EN/ISO/IEC designation, neither of which an
`STN …`/`TNI …` designation is — which is exactly why these 391 records
were never fetched by either. A new `--only-missing-description` flag keeps
a run targeted at the actual gap rather than re-querying a public registry
for data the corpus already holds.

### 17.5 Outcome of the fetch tier (2026-09-16)

126 Slovak designations looked up, **121 resolved in the registry (96 %)**,
**91 carrying real scope text** (median 729 characters — comparable to the
611-character average of the authentic abstracts already in the corpus).
The 5 that did not resolve are all amendments or collection markers
(`/A1`, `/Zmena`, `(súbor)`), refused rather than approximated. A further
29 resolved but the registry publishes no scope for them.

All 91 were then translated to Czech by `src/tools/translate_annotations.py`
(31 from Slovak, 60 from English), 0 failures, every result verifying as
Czech and every original preserved under `description_source`.

One overreach caught in testing: a detector-only rule ("translate anything
that doesn't look Czech") pulled in two `zakonyprolidi.cz` entries that are
already Czech — `detect_language()` reads a short Czech legal title as
Slovak. `TRANSLATABLE_DOMAINS` is now an explicit allow-list; a new domain
opts in deliberately.

### 17.6 The synthesis tier (2026-09-17, user-directed)

For the remaining **34** — 29 the registry knows but publishes no scope
for, 5 it has no exact match for — `src/tools/synthesize_summaries.py`
writes an approximate Czech summary. Per the user's direction, synthesis
is the fallback *"in case that no abstract is available"*, and it is
reached only after the fetch tier has genuinely failed for that record.

**The input is the standard's title and nothing else**, because nothing
else exists: no publisher scope, and no full text (standards are
copyrighted, `fetch_fulltext.py` skips `typ_dokumentu == "Norma"`
unconditionally, §4). The design therefore keeps that visible rather than
papering over it:

- written to its own `data/synthesized_summaries.json`, never into
  `site_metadata_cache.json` (which means "fetched from the source");
- carried into `popis_priblizny` only — `build_unified_db.apply_synthesized_summary()`
  refuses outright if the record already has a `popis_autoritativni` or an
  `anotace_poznamka`, so an approximation can never displace a real
  description;
- `Document.description` stays **empty** and `needs_review` stays **set**:
  the record still has no real description;
- the UI renders it under **"Přibližné shrnutí, neověřeno"**, and
  `/export/<fmt>` does not carry it at all, so no downstream consumer
  receives a title restatement as if it were a description.

The prompt is narrow for the same reason §13 exists: the model is told to
restate the subject the title names and is explicitly forbidden to add
figures, limits, pressures, temperatures, test procedures or applicability
claims the title does not state. The results bear that out —
*"Kovové tlakové nádoby na dopravu plynov. Prevádzkové pravidlá"* becomes
*"Norma se týká provozních pravidel pro kovové tlakové nádoby určené k
dopravě plynů."* and nothing more.

### 17.7 Result

`src/tools/backfill_descriptions.py` applied both tiers to the live
database. Of 391 STN/TNI standards: 280 already had a description, **77
gained the publisher's own scope text** (translated), **34 gained an
approximate summary**, and **0 were left with neither**.

Corpus-wide: descriptions **780 → 857 of 1238 (63 % → 69 %)**,
`needs_review` **450 → 374**, records still flagged for a missing
description **435 → 358**. Zero records carry an approximate summary
alongside a real description.

What remains unaddressed is the rest of §17.2's table — `iso.org` (73,
and ISO actively blocks automation per §4), `dvgw.de` (42),
`webstore.iec.ch` (17), `eiga.eu` (16), `bveg.de` (14) — each needing its
own `src/sites/` module on the same resolve-then-extract pattern, plus the
23 `Bibliografický pramen` rows, which never pass through any
`database_*.json` and are already full citations.

## 18. Three-tier `needs_review` severity — most of it isn't a defect (NEW, 2026-09-17, user-directed)

**User direction:** continue with Phase 4 of the demo/handover plan
(doc/PLAN.md §16's context) — split the flag so "incomplete" and "wrong"
stop reading as the same thing.

Before this, `needs_review` was one undifferentiated red "Vyžaduje
kontrolu" badge for whatever reason `detect_data_quality_issues()`
(`init_db.py`) or the language/EU-gestor backfills ever set it for. Live
count: **374 of 1238 documents (30 %)** flagged, but only **8** of those
are an actual defect (7 fragment titles, 1 unresolved EU gestor — 0
garbled designations currently). The other 366 just mean "this record is
incomplete" (358 missing a description, 55 with an auto-detected,
unverified language — the two overlap on some records), which is a much
less alarming claim than the shared red warning treatment implied.

New `classify_review_severity()` (`app/app.py`) classifies a flagged
document into exactly one of three severities, matched by substring
against the five distinct reason templates the whole pipeline currently
produces (`init_db.py:281-285`, `backfill_eu_gestor.UNRESOLVED_REVIEW_REASON`):

- **defect** — a garbled designation, a fragment title, or an unresolved
  EU gestor. Keeps the red/amber "Vyžaduje opravu" warning treatment.
- **approximate** — no real description, but `popis_priblizny` carries a
  title-derived summary (§17). Rendered "Přibližné shrnutí, neověřeno".
- **incomplete** — everything else (missing description with no fallback
  summary either, or just an uncertain auto-detected language). Rendered
  "Neúplné" in a calm, non-alarming style — informational, not a warning.

Measured on the live corpus: **8 defect / 34 approximate / 332
incomplete**, summing exactly to 374, zero overlap between defect and
approximate (a garbled/fragment record that also happens to lack a
description still reads as "defect" — the more serious claim wins).

`review_badge(doc)` is the single template-facing call
(`@app.template_global()`), returning `{severity, label, icon}` or `None`.
Rendered in `index.html`'s row badge (all three severities, same compact
slot as before) and `document.html`'s header banner — **except
'approximate' there**, deliberately: the Popis panel immediately below
already shows the identical "Přibližné shrnutí, neověřeno" marker right
next to the summary itself, so repeating it in the banner above would be
the same claim said twice in the same viewport without scrolling. The
list row doesn't have this problem — the badge sits in the collapsed
summary, the same marker (already wired in §17.7) only appears once a row
is expanded, so summary-then-detail is the normal pattern there, not
duplication.

New CSS severity variants on `.review-flag`/`.review-banner`: `.is-defect`
(red), `.is-approximate` (the same amber as `.approximate-label`, since
it is the same claim in a different-shaped element), `.is-incomplete`
(muted gray, explicitly not amber/red — the one thing this section exists
to fix). 11 new tests in `tests/test_app_export.py`'s
`ClassifyReviewSeverityTestCase`, including the dynamic-suffix matching
(EU-gestor/language reasons carry a "(...)" tail) and the defect-wins-over-
approximate ordering. 611 tests total, all passing. Verified live: HTML
still well-formed on every affected page, and the three severities render
with visibly distinct styling.

## 19. Handover setup — requirements.txt, .env.example, PROJECT.md (NEW, 2026-09-17, user-directed)

**User direction:** continue with Phase 5 of the demo/handover plan
(§16's context) — a partner cloning this repository could not install it
(no dependency manifest existed at all — `langdetect`, added 2026-09-15,
was undeclared), could not configure it (`.env` is gitignored with no
template), and `PROJECT.md` did not get them to a running app (wrong
port, wrong paths, no database setup at all).

**`requirements.txt`** — pinned exact versions (`==`, not floors) from
the working development venv, scoped to what the app and the documented
pipeline order actually import: Flask, PyMySQL, python-dotenv, requests,
langdetect, openai, openpyxl, pdfplumber, python-docx, beautifulsoup4.
`lxml` was considered and left out — every `BeautifulSoup(...)` call in
`src/sites/`/`src/tools/check_csn_validity.py` explicitly passes
`"html.parser"`, so nothing in this codebase actually needs it, pinned or
not. `pandas` and `duckduckgo_search` (used only by the `analyze_*.py`
exploratory scripts, `process_laws.py`, and `search_agent.py` — none of
them part of the app or the pipeline) went into a separate
`requirements-optional.txt` instead of bloating the default install.

Verified, not assumed: installed `requirements.txt` into a genuinely
fresh venv (no pip cache reuse of the dev environment) and imported every
module the app and pipeline touch against it — `app.app`, all five
`src/sites/*` modules, and all 27 `src/tools/*` pipeline/enrichment
scripts this session's work produced or touched. All import cleanly; one
of them (`deduplicate_db.py`) even exercises the real `.openapi_key`
loading path as an import-time side effect.

**`.env.example`** — the five `DB_*` keys `app/app.py` and every
`src/tools/` script actually read, no values. Confirmed the key names
match the real (gitignored) `.env` exactly. `.openapi_key` needed no
template of its own — verified it is correctly gitignored, was never
tracked, and appears nowhere in git history.

One real finding while writing it: `provision_db.py` used to issue
`CREATE DATABASE IF NOT EXISTS` using the APP's own `.env` credentials,
which needs a global `CREATE` privilege — but this project's own live
account (`h2regdocs`@`localhost`) only has `GRANT ALL` scoped to the
`h2regdocs` database itself, confirmed by `SHOW GRANTS` (this is also why
no scratch database could be created to run a true end-to-end rebuild
rehearsal in §16's verification — the same constraint). So this
deployment's own database was necessarily provisioned by some OTHER,
undocumented account, and `.env` alone could never fully provision a
fresh environment.

**User decision, immediately following**: the app account should never
need that privilege in the first place. `provision_db.py` was rewritten
to use a separate admin identity, supplied only for this one bootstrap
(`--admin-user`/`--admin-password`, `DB_ADMIN_USER`/`DB_ADMIN_PASSWORD`,
or an interactive prompt — never `.env`), to create both the database
and the app's own narrowly-scoped user, which then applies the schema
itself. Also noted along the way: `provision_db.py` shells out to the
`mariadb` CLI client (present on this machine, but a system package, not
a Python dependency `requirements.txt` can express).

**2026-09-17 follow-up — live-verified, not just reasoned about.** Added
`--env-file` (provision a second, disposable database/user pair without
touching the real `.env` — e.g. `.env.test` → `h2regdocs_test`) and
`--schema-only` (the database/user already exist — created ahead of time
by someone with admin access — so skip the bootstrap entirely and just
clear + reapply the schema using the already-created app account alone,
no admin credentials needed at any point). Run for real against a live
MariaDB instance: `h2regdocs_test` was created by hand with its own
scoped account, then `provision_db.py --env-file .env.test --schema-only`
applied all 34 tables cleanly; run a second time, it dropped all 34 and
reapplied them identically. This closes the gap described below.

**`PROJECT.md` refresh** — corrected every stale claim found: the
architecture section still described SQLite (`db/regulatory_documents.db`,
`db/init_db.py`) and CSV-format data, both long superseded by MariaDB and
the JSON/XLSX pipeline; the directory table didn't mention `src/sites/`,
`requirements.txt`, or that `/doc` now holds substantial documentation
(it used to say "zatím prázdné"); and "Používání" said `python app.py` in
`app/` on port 5000 (it is 5050, via `app/app.py` for development or
`wsgi.py` for a real deployment).

The rebuilt "Instalace a spuštění" walkthrough deliberately does **not**
start from `build_unified_db.py`/`deduplicate_db.py` — `data/
database_merged_deduplicated.json` (the pipeline's own output) is already
committed to the repository, so the minimal path to a running app is
`init_db.py` → `load_document_relations.py` → `load_process_layer.py`
directly against it. Regenerating the corpus from the original partner
spreadsheets is a separate, longer, and — per §1's own recorded lesson —
not-safe-to-re-run-casually process, pointed at `doc/PLAN.md` rather than
duplicated in PROJECT.md.

**What was left unverified at the time of writing, now closed**: whether
`provision_db.py` and the full install actually succeed end to end
against a brand-new, empty MariaDB instance. The account available in
this environment cannot itself create one — no passwordless sudo,
`root@localhost` access denied — so this originally could only be
verified as far as possible without a more privileged account: every
Python-side step (install, imports, the app running, the full test
suite) was exercised for real, but the SQL-provisioning step was only
read and reasoned about. The 2026-09-17 follow-up above closes that gap:
the user provisioned a scratch database/account by hand, and the
`--schema-only` path was run against it for real, twice.

## 20. Parser pass — filling `node_edge`/`node_variability`/`node_document.SOURCE` (NEW, 2026-09-17, user-directed)

**User direction:** continue with Phase 2 of the demo/handover plan
(§16's context), then Phase 3 — the process view needs this data to not
look sparse. All changes are in `src/tools/parse_v02_processes.py` and
`src/tools/load_process_layer.py`.

**Citations.** `_CITATION_PATTERNS` gained two entries: a bare
`EN\s+\d{4,5}` pattern (U7 cites `EN 17124:2022`/`EN 17127:2020` with no
`ČSN`/`STN` prefix — a negative lookbehind keeps it from also
re-matching the tail of an already-whole `ČSN EN NNNN-N` citation
elsewhere), and a second-coordinated-act pattern
(`č.\s*NNNN/YYYY\s*\(ABBR\)`) for phrases like U4's *"nařízení EU
č. 1907/2006 (REACH) a č. 1272/2008 (CLP)"*, where only the first act
carries its own `EU`/`ES` prefix. Live result:
`node_document.LEGAL_BASIS` rose from the baseline 35 to **38** (CLP,
`EN 17127`, one more from the node→document mapping table). `EN 17124`
stayed correctly unmatched — the corpus has `ČSN EN 17124` and
`STN EN 17124/ - 2022.06` but no bare `EN 17124` identifier, so exact-text
matching refuses to guess between them, the same principle already
applied to `EN ISO 17268` (doc/PLAN.md:1168).

**Edges and variability.** Both `node_edge` (15 rows) and
`node_variability` (28 rows) are already seeded by static `INSERT`s in
`Konsolidace-DB-schema.sql` — `direction`/`character`/`intensity_code`
came from `Konsolidace-DB-popis.md` §4.10/§6, not the docx. What was
missing was the prose: `description`/`specifics`, both `NULL` in every
row. The parser now extracts each node's own "Vazby na další uzly
procesní sítě" (2-col table: target node, character-and-description
text) and "Variabilita procesu podle typu vodíkové instalace" (3-col:
installation-type label, specifics prose, intensity) sections;
`load_process_layer.py` **`UPDATE`s** the existing seeded rows rather
than inserting new ones — matching an edge against a seed row considers
both directions when the seed says `BIDIRECTIONAL`, but never guesses
past that.

That surfaced a real, substantive disagreement between the source docx
and the static seed: of 33 node→node edge mentions across all 7 nodes'
own sections, only **19 matched** an existing seeded row's exact
(from, to[, BIDIRECTIONAL]) shape; the other **14** — including the
already-known missing `U1↔U5` pair, but also several where the seed's
`DIRECT` direction runs opposite to how a node's own section describes
the relationship (e.g. seed has `U6→U2`, docx's U2 section describes it
from U2's perspective) — went to `data/process_layer_review_queue.json`
as `unmatched_node_edge`, for a human to decide whether the seed's
direction/character needs correcting rather than the code silently
picking one. `node_variability` had no such ambiguity: all 28 docx rows
matched their seeded (node, installation_type) row directly (the map
`installation_type.code -> docx "Oblast" label` was confirmed against
all 4 real values first). Live result: `node_edge.description` populated
for 14/15 rows (the 15th, `U3→U4`, is only ever described from `U4`'s
side in the docx, which doesn't match the seed's `U3→U4` direction — it
now correctly shows up as `unmatched_node_edge` too, not silently
picked one way);`node_variability.specifics` populated for all 28/28.

**`[N]` bibliography refs, node-scoped.** V02's legal-basis prose cites
bibliography entries inline (e.g. U4's *"...živnostenského oprávnění
[6]..."*), not just in the "Seznam použité literatury" list itself —
previously invisible to the loader entirely. `extract_bracket_refs()`
sweeps each node's full prose (not just the legal-basis section — never
assumed confined to it) for `[N]` markers; `load_bibliography()` now
returns a `{ref_id: Document.id}` map (built while it resolves/creates
each entry, which it always did — just never returned before), and a
new `load_node_bibliography_links()` uses it to insert
`node_document` rows with `link_type='SOURCE'`, run in a second pass
after `load_bibliography` (needs its map). Live result: **33** `SOURCE`
rows created (previously 0), giving the 22 `Bibliografický pramen`
`Document` rows real node-level context — a citation like U4's HYTEP
`[6]`-`[10]` references now resolve to actual linked documents.

**A pre-existing gap found while testing, unrelated to this step but
blocking it**: `load_process_layer.py`'s `RESET_ORDER` truncates layer
B/C tables on every run, but never `Document`/`DocumentVersion` — so
`load_bibliography()`'s "create a new Document for genuinely new
material" branch duplicate-inserts on a second run, colliding on the
content-derived slug. Not fixed here (out of this step's scope — the
documented, correct fix is to run the full pipeline, `init_db.py`
included, before re-running this script, which re-TRUNCATEs `Document`
first); worth a real fix later so this script tolerates being re-run on
its own.

**Also found and fixed**: testing this required a full pipeline rebuild
(`build_unified_db.py` → `deduplicate_db.py` → `init_db.py` →
`load_document_relations.py` → `load_process_layer.py`, skipping
`fetch_authoritative_metadata.py` since `site_metadata_cache.json`
already held everything needed, no new network fetches required) — an
earlier, isolated `init_db.py` run (before realizing this) had briefly
regressed the live database's `needs_review` count back from 374 to 450,
because §17's fetched/synthesized descriptions were applied to the live
database directly by `backfill_descriptions.py`, never written back
into `database_merged_deduplicated.json` — so a bare `init_db.py`
re-import (without first re-running `build_unified_db.py`, which
reapplies both caches) silently loses them. The full rebuild restored
`needs_review` to 375 (previously 374 — one record's boundary shifted,
not a regression) and correctly re-baked both tiers into the JSON. This
is the same "silently discarded on next rebuild" failure mode §17.1
flagged for `enrich_annotations.py`, now also true of
`backfill_descriptions.py`'s direct-DB-write path — worth fixing
properly (e.g. writing the two caches' effect back into
`database_merged_deduplicated.json` too, not just the live DB) before
`init_db.py` is ever run again without a preceding full rebuild.

Test suite: 38 tests in `test_parse_v02_processes.py` (was 24), covering
`extract_bracket_refs`, `parse_edge_target`, `map_installation_type`, and
the two new citation patterns; `load_process_layer.py`'s new
`load_node_edges`/`load_node_variability`/`load_node_bibliography_links`
are orchestration (DB cursor calls), verified live rather than
unit-tested — same division the module's docstring already establishes
for its other loader functions. Full suite: 644 tests, all passing
(including `test_search.py`, which needs the live DB and now has one).
One test-isolation bug found and fixed along the way: the new
`--env-file` test in `test_provision_db.py` called
`load_dotenv(..., override=True)`, which leaked its fake `DB_HOST=
testhost` etc. into the shared `unittest discover` process and broke
`test_search.py` when run as part of the full suite (passed in
isolation, failed with 500s in the full run) — fixed by wrapping that
one test in `mock.patch.dict(os.environ)` to restore the real values
afterward.

## 21. The process view — `/procesy` and `/proces/<node_id>` (NEW, 2026-09-17, user-directed)

**User direction:** Phase 3 of the demo/handover plan (§16's context) —
the layer-C "process view has never been referenced by `app/app.py`"
gap, chosen as the strongest remaining demo story, done right after §20
so it would have real edge/variability/SOURCE data to show rather than
the bare 15/28/0-row state.

Two new routes in `app/app.py`, `fetch_process_overview()` and
`fetch_node_detail()`, copying `fetch_document_detail()`'s shape exactly
(one function, one cursor, sequential queries, a plain dict
`render_template` splats):

- `GET /procesy` — all 7 nodes, the 4×7 variability matrix
  (`intensity_level.label` renders directly, no extra formatting logic
  needed — it's already `"●●● klíčový"` etc. in the seed), and the
  `node_edge` graph as a plain list (no diagramming library — the CSP
  only allows scripts from a fixed cdnjs/jsdelivr/tailwind/jquery
  allow-list, and a text list was judged clearer than a forced diagram
  for 15 edges anyway).
- `GET /proces/<node_id>` — node, description (purpose/role/trigger/
  key-decision-point), branches with steps, inputs, outputs, subjects,
  problems, both-direction edges, this node's row of the variability
  matrix, and its linked documents split by `link_type`
  (`LEGAL_BASIS`/`SOURCE`, phrased differently: "právní opora"/"pramen").
- Reciprocal **"Procesní uzly"** panel added to `fetch_document_detail()`/
  `document.html` — the same `node_document` table read from the other
  side, so a document page links back to every node that cites it. This
  is the actual demonstration that layer C works both ways: verified
  live by opening a HYTEP source document (`SOURCE`, 3 nodes) and a
  `283/2021 Sb.` legal-basis document (`LEGAL_BASIS`, 2 nodes) — both
  showed the correct reciprocal node list.
- "Procesy" tab in `base.html` (previously `href="#"`), both tabs now
  correctly highlight `active` via `request.endpoint`.

**Reused, not reinvented**, exactly as planned: `.doc-panel`/`.doc-meta`/
`.doc-table`/`.doc-relations`/`.relation-type`/`.meta-tag`/`.badge`/
`.doc-designation`, and — for a node's branches — the identical
`.document-row`/`.row-visible`/`.row-details`/`.expand-icon` accordion
markup `index.html` already uses, so `base.html`'s existing toggle JS
(which targets `.document-row` generically, not scoped to the catalogue
page) works on `/proces/<id>` with no JS changes at all. Small,
genuinely new CSS only for what had no existing equivalent: a responsive
node-card grid (`.process-nodes-grid`, the same `repeat(auto-fit,
minmax(...))` pattern `.filters-grid` already uses, kept as its own
class since "filters" would be a misnomer here), a horizontal-scroll
wrapper for the 7×4 matrix table at phone width, and a numbered
step-list style for branch steps.

Two judgement calls resolved as the plan flagged: `node_description
.v01_link_description` (e.g. U1's *"Databáze umožňuje filtrovat, které
právní předpisy... jsou relevantní pro konkrétní typ instalace"*) is
**not rendered at all** — it describes a filter-by-installation-type
capability this app doesn't have, and rendering it verbatim on the page
itself would read as a live promise, not V01's own design note it
actually is. U1/U3's `node_output.document_name` (a full sentence, not a
short title) is rendered as prose in a `<ul>`, not force-fit into a
table cell — the same markup now serves both the branched nodes' short
document names and the two linear nodes' paragraph-length ones without
a special case.

Verified live end to end: all 7 `/proces/<id>` pages return 200, a
missing node id (`/proces/U9`) returns 404, `/procesy` renders all 7
cards, the 4×7 matrix, and 15 edges. Full suite: 644 tests, all still
passing.

## 22. Two rerun-safety bugs, found and fixed (NEW, 2026-09-17, user-directed)

**User direction:** having committed §20/§21's Phase 2/3 work, fix the
two correctness bugs §20 found but deliberately left unpatched.

**Fix 1 — `load_process_layer.py` Document duplication on a lone
re-run.** The 22 `Bibliografický pramen` `Document` rows
`load_bibliography()` creates are 100% synthetic (sourced only from the
docx bibliography, never from `database_merged_deduplicated.json`), so
re-deriving them fresh on every run is always correct — but
`RESET_ORDER` never cleared `Document`/`DocumentVersion`, so a second
run duplicate-inserted them and collided on the content-derived slug.
Added `reset_bibliography_documents()`, run right after
`reset_layer_b_tables()` (which already clears `node_document`, so no
FK conflict) — deletes `DocumentVersion` then `Document` rows whose type
is `Bibliografický pramen`. Confirmed live via
`information_schema.KEY_COLUMN_USAGE` first that no other table
(`node_activation_rule`, `scenario_document`, `DocumentKeyword`,
`document_relation`) references any of these 22 rows.

**A second bug surfaced while verifying the first**: running
`load_process_layer.py` twice in a row (the exact rerun-safety test Fix
1 needed) produced 46 review items instead of 18 — 28 spurious
`unmatched_node_variability` entries. Cause: `load_node_variability()`
used the `UPDATE`'s own `cursor.rowcount` to detect a match, but
MariaDB's default client reports *changed* rows, not *matched* rows —
on the second run `specifics` was already set to the identical value, so
every row looked unmatched even though all 28 plainly were. Fixed by
`SELECT`-then-`UPDATE` (existence checked separately from the write),
the same pattern `load_node_edges()` already used for its own
match-then-merge logic. Verified: two runs back-to-back now both report
18 review items, and `Bibliografický pramen`/`node_document`
`LEGAL_BASIS`/`SOURCE`/`node_edge`-with-description/
`node_variability`-with-specifics counts (22/38/33/14/28) are stable
across both.

**Fix 2 — `backfill_descriptions.py` retired, not patched.** Confirmed
by reading both side by side: `build_unified_db.py`'s
`apply_authoritative_metadata()`/`apply_synthesized_summary()` already
do the exact same job — same cache files
(`data/site_metadata_cache.json`, `data/synthesized_summaries.json`),
same `stn:<designation>`/`<designation>` keys, same target fields — but
correctly, through the JSON pipeline, on every full rebuild; and
`init_db.py`'s `detect_data_quality_issues()` already computes
`needs_review`/`review_reason` from the *resolved* description, so the
"chybí popis/anotace dokumentu" reason clears itself with no separate
reason-stripping step needed. `backfill_descriptions.py` was therefore
fully redundant, not merely close — marked SUPERSEDED in its own
docstring and in `src/tools/0README.md` (kept, not deleted, as a
historical record and for its dry-run reporting shape); any future
annotation-fetch round should end with the full pipeline rebuild
instead.

**Verification**: a complete pipeline rebuild
(`build_unified_db.py` → `deduplicate_db.py` → `link_document_versions.py`
→ `link_document_relations_auto.py` → `init_db.py` →
`load_document_relations.py` → `load_process_layer.py`) with both fixes
applied reproduced exactly `needs_review` 375/1215 — the same figure §20
recorded, confirming no regression. Full suite: 644 tests, all passing.
App smoke-check: `/`, `/procesy`, `/proces/U4` all 200, `/proces/U9` 404.

## 23. Domain-based language override — e-sbirka.gov.cz can't host Slovak (NEW, 2026-09-17, user-directed)

**User direction, raised mid-session**: Czech national laws were showing
up with `language='SK'` — langdetect confusing a short Czech legal title
for Slovak (the two languages are close enough that this happens; the
existing `CONFIDENCE_THRESHOLD` guard didn't catch it because the wrong
guess was itself confident, not borderline). Live-confirmed: 2 of 32
`e-sbirka.gov.cz`-hosted `Document` rows had `language='SK'` (ids 69, 78
— `76/2002 Sb.` and `133/2010 Sb.`), both with `needs_review=0` — a
confidently wrong guess, not a flagged uncertain one.

`e-sbirka.gov.cz` is the Czech Republic's own official legal-register
portal (Sbírka zákonů) — it structurally can only ever publish Czech
legislation, so this is a known fact about the source system, not
something to detect at all. Added
`resolve_domain_language_override(url)` to `src/tools/language.py`
(`DOMAIN_LANGUAGE_OVERRIDES`, currently just the one entry) — checked
**before** both `normalize_raw_language()` and `detect_language()` in
both call sites (`init_db.py`'s per-import resolution and
`backfill_language.py`'s one-time DB backfill), since the domain fact
must be able to override even an already-stored, confidently-wrong
value — the existing `normalize_raw_language()`-first short-circuit in
`backfill_language.py` would otherwise never revisit an already
CS/SK/EN/DE-shaped value.

Applied live via `backfill_language.py --apply`: 2 corrected by the
domain override (ids 69, 78, now `CS`), plus 22 unrelated
`Bibliografický pramen` rows (§20's synthetic bibliography Documents,
which `load_bibliography()` never set a `language` for at all) picked up
a real detected language as a side effect of the same run — legitimate,
in scope for what this script already does, not a side effect worth
guarding against.

4 new tests in `tests/test_language.py`
(`ResolveDomainLanguageOverrideTestCase`). Full suite: 648 tests, all
passing.

## 24. Phase 1 continued — `eiga.eu` (NEW, 2026-09-17, user-directed)

**User direction:** continue Phase 1 (§17.2/§17.7's remaining domains:
`iso.org` 73, `dvgw.de` 42, `webstore.iec.ch` 17, `eiga.eu` 16,
`bveg.de` 14). Investigated feasibility live for each before picking one
— `iso.org` (highest count) confirmed **blocked**, a real per-document
URL already stored for 6 corpus records returns HTTP 403 to a plain
fetch, matching §17.7's existing note. `eiga.eu` chosen as most
tractable; `dvgw.de`/`webstore.iec.ch`/`bveg.de` deferred — see the plan
file `linear-squishing-sky.md`'s "Deferred" section for what was found
and why (short version: `dvgw.de`'s real catalog is a separate,
apparently JS-rendered portal; `webstore.iec.ch` uses numeric publication
IDs with no visible designation-search endpoint; `bveg.de` records have
no designation/`znacka` at all to search by).

**Getting to a working query took two dead ends first, worth recording**:
the site's own `<form>` markup for its "Search & Filter Pro" listing
advertises `_sf_search[]`/`_sft_ct_doc_cats[]` fields, and even its own
documented AJAX endpoint (`?sfid=1550&sf_action=get_data&sf_data=results`)
— both returned HTTP 200, both silently ignored the query and returned
the unfiltered default listing. An initial WebFetch-summarized read of
the page had suggested a working search was already confirmed; it
wasn't — real `curl`/`requests` testing showed otherwise, a correction
made explicitly to the user rather than building further on the
unverified premise. The user, doing their own research in parallel,
supplied the parameter that actually works:
`GET /publications/?_sf_s=<digits>`.

**New `src/sites/eiga.py`**, same shape as `normoff.py` (corpus stores
only the `eiga.eu` homepage, never a per-document URL, so `resolve()`
precedes `extract()`) but with a twist `normoff.py` doesn't need: there
is no separate detail page — the search listing itself already carries
the scope text, in a "READ MORE" `<div>` present in the raw HTML (hidden
via inline `display:none`, not JS-rendered). `normalize_designation()`
strips the corpus's `EIGA`/`IGC` label words and takes the first digit
run (`"EIGA IGC Doc 100/20"` -> `"100"`), matching the site's own
numbering. The site's search is minimum-3-digits and, below that or for
a number with no current document, returns fuzzy full-text hits instead
of nothing (live-confirmed: querying `"100"` returned 10 unrelated
documents, `"121"` — a corpus designation with no current match —
returned 2 unrelated ones) — trusting "the first result" would
therefore silently attach the wrong document's description to the wrong
record. `extract()` guards against this by re-verifying the winning
result's OWN leading number (parsed from its title) against the query
digits embedded in its own URL, never trusting proximity or ranking.
Falls back to a `pdfplumber`-extracted PDF first-page lead when a
listing entry has no visible summary (rare in practice). 14 tests in
`tests/test_sites_eiga.py`, all against real HTML captured from the live
site (no network in the suite).

**A live-testing wrinkle, resolved, not a lasting problem**: eiga.eu
sits behind a Sucuri WAF that started intermittently returning HTTP 403
partway through manual testing — flipping between 200 and 403 for the
identical request seconds apart, not consistently tied to `curl` vs
`requests`. Flagged to the user as a real operational risk before
running the actual batch fetch; by the time of the real run (fewer,
better-paced requests, mixed in with the orchestrator's existing
per-request `SLEEP_SECONDS` delay from other domains' lookups ahead of
it in corpus order) it completed cleanly, 16/16, no blocking.

**A real integration gap found and fixed while verifying the live
run**: the fetch side (`fetch_authoritative_metadata.py`'s new
`is_eiga_norm_record()` branch, `eiga:<designation>` cache key) was
wired up correctly, but `build_unified_db.py`'s
`apply_authoritative_metadata()` — the function that actually reapplies
`site_metadata_cache.json` into a rebuilt `database_merged_deduplicated
.json` — only knew to check a record's URL, then `csn:<znacka>`, then
`stn:<designation_core(znacka)>`; it had never been taught about
`eiga:<designation>` keys at all. The cache had the right data; nothing
applied it. Exactly the class of gap this session's own §20 already
flagged once (fetch wired, apply not) — caught here by re-running the
full pipeline and checking a specific record by hand rather than trusting
`build_unified_db.py`'s summary counts alone. Fixed by adding the
`eiga:` lookup branch (keyed on `eiga.py`'s own `normalize_designation()`,
not `designation_core()` — a different numbering convention). New test:
`ApplyAuthoritativeMetadataTestCase.test_eiga_key_used_when_no_url_or_csn_stn_match`.

**Result**: 16 EIGA designations looked up, 11 resolved with real scope
text (5 correctly refused — genuinely too-short codes or a designation
with no current match, e.g. `"EIGA 121/14"`, not guessed at). All 11
translated to Czech (`translate_annotations.py`, along with 4 leftover
untranslated STN entries from an earlier round), spot-checked by hand
against the live site before trusting the batch. Full pipeline rebuild:
`needs_review` 375 → 366/1215, 14 `EIGA`-identifier `Document` rows now
carry a real description (more than 11 distinct designations — several
are cited by more than one raw record across sources). Full suite: 663
tests, all passing. App smoke-checked live: `/`, `/procesy`,
`/proces/U4` all 200, and `EIGA DOC 246` now shows its real description
in a live search.

## 25. Phase 1 continued — `iec.ch`/`webstore.iec.ch` (NEW, 2026-09-17, user-directed)

**User direction:** continue Phase 1 with the IEC domain (17-19 corpus
records), proposing a specific mechanism: the "IEC technical committees
and subcommittees" list at `www.iec.ch/technical-committees-and-
subcommittees#tclist`, whose "Publications" column links to a
per-committee overview page carrying a `javascript:openPopup(...)` call
that exports that committee's publication list as XLS, including scope
text.

**Feasibility check, live, before writing anything**: `www.iec.ch`
(needed for both the committee list and the per-committee export) sits
behind an **AWS WAF Bot Control "challenge" action** — confirmed via
response headers (`x-amzn-waf-action: challenge`, HTTP 202, empty
body) — a JS proof-of-work/fingerprint challenge, not a header or
rate-limit problem a plain `requests`/`curl` client can work around
(unlike `eiga.eu`'s WAF, or `iso.org`'s simple 403). `webstore.iec.ch`
itself (where the corpus's 19 IEC-related records already point, as a
shared catalog-root URL, same shape as the STN/EIGA problem) is NOT
behind this WAF and serves real per-document pages — but its own
search results are entirely client-side JS-rendered ("JavaScript seems
to be disabled in your browser" is literally what a plain fetch sees),
so there is no way to resolve a designation into one of those pages
without JS either.

**User proposed headless-browser automation as the way through — tried
live, with the user's help getting past two real environment gaps**:
- Playwright installed cleanly (`pip install playwright`,
  `playwright install chromium` — downloads its own Chrome-for-Testing
  binary, no system package needed for the binary itself).
- Launching it failed on a missing system library
  (`libxkbcommon.so.0`), and `playwright install-deps chromium` (which
  installs the *whole* set of Chrome runtime libraries in one shot, not
  library-by-library) needs root — this session has none (same
  standing limitation as the MariaDB admin situation, doc/PLAN.md §19).
  **The user ran `sudo .venv/bin/playwright install-deps chromium`
  themselves** — after that, headless Chromium passed the WAF challenge
  on the first try.

**The `openPopup()` mechanism, read directly off the rendered page**:
resolves to `f?p=103:75:0::::FSP_ORG_ID,FSP_LANG_ID,FSP_EXPORT:
<org_id>,25,XLSX` — a plain URL, once a committee's own `FSP_ORG_ID` is
known (read straight off the committee-list table's own links, 224
committees found live). Triggering it via Playwright's
`expect_download()` reliably raises a `"Download is starting"` error
from `page.goto()` — Playwright's own signal that navigation turned
into a file download, not a real failure; the download itself still
fires and is captured regardless (had to learn this the hard way: a
first, naive version treated it as a real failure and every single one
of 224 committees "failed").

**Two IEC designations don't encode which of the ~224 technical
committees publishes them** — unlike `normoff.py`/`eiga.py`, there is no
per-designation live search to do at all, only a bulk harvest across
every committee's own export. New `src/tools/harvest_iec_publications.py`
does exactly that: Playwright navigates the committee list once, then
downloads and parses each committee's XLSX (columns `Reference | Edition
| Corrigenda/IS | Date | Title | Language | Description`) into
`data/iec_committees/<org_id>.json` (idempotent — a committee already
harvested is skipped unless `--force`, same convention as
`site_metadata_cache.json`), then aggregates all of them into
`data/iec_publications_index.json` keyed by `reference_base()`
(`"IEC 60050-102:2007"` -> `"IEC 60050-102"` — the edition year isn't
part of a document's own identity). Amendment/corrigendum rows
(`/AMD1:2017`, `/COR1:2023`) never carry a description of their own —
confirmed live across all 265 of TC 1's own publications, 0 exceptions —
so they never enter the index; when a base reference appears more than
once (a superseded edition still listed), the entry with the latest
`date` wins, same "prefer most recent" rule `normoff.py` already uses.
`clean_description()` strips real HTML markup (not just `<br/>` — a
first version left `<!-- NEW! --><a href="...">...</a>` "a newer
edition is out" announcements in verbatim, caught by comparing against
the raw XLSX cell) via `BeautifulSoup(...).get_text()`, plus a stray
Excel `_x000D_` artifact.

**Live harvest result**: all 224 committees, 21552-byte-average XLSX
per committee, **10,571 base references with a real description**. New
`src/sites/iec.py` is the lightweight, network-free consumer — reads
only the local index, never touches Playwright or the network itself,
so the normal `fetch_authoritative_metadata.py` pipeline stays as cheap
as it's always been for every other domain.
`normalize_designation()` handles three corpus-side quirks found by
testing against the real 19 records: the Sinay edition suffix
(`"/ - 2003.06"`), a `"prEN "` prefix (the corpus's own marker for a
draft European adoption, not part of the IEC document's identity), and
— found only once matching against the real harvested keys — the
corpus writes `"IEC/TR"`/`"IEC/TS"`/`"IEC/PAS"` slash-joined while IEC's
own catalog spells it space-separated (`"IEC TR 62351-13:2016"`).

**A second real bug found while verifying live, more consequential than
it looks**: `apply_authoritative_metadata()`'s fallback cascade (URL ->
`csn:` -> `stn:` -> `eiga:` -> `iec:`) used a bare `entry is None` check
to decide whether to try the next key. Every bare `"IEC ..."` znacka
already had a **stale, `"failed"` `csn:<znacka>` entry** cached from
*before* `is_iec_norm_record()` existed (a bare `IEC`/`EN`/`ISO`
designation matches `is_csn_norm_record()`'s own bare-international
pattern, so these records used to fall through to the ČSN branch, which
correctly found no adoption and cached that as `"failed"`) — with the
old check, that stale failed entry was found FIRST and silently
prevented the new `iec:` key from ever being tried, even though it held
the real, fetched data. First rebuild attempt: `apply_authoritative_
metadata()` reported 480 records touched (barely more than before IEC
was added), and a specific record checked by hand still showed
`needs_review=1`, no description — caught by spot-checking a named
record rather than trusting the aggregate count alone, the same
discipline that caught the EIGA-side gap in §24. Fixed with a new
`_fetched_cache_entry(cache, key)` helper that only ever accepts a
`status == "fetched"` entry, tried in the same priority order as
before, `None` otherwise — a general fix, not just for IEC (the same
latent bug could have affected STN too, if an old ČSN attempt happened
to precede it for some record). New regression test:
`test_stale_failed_entry_under_an_earlier_key_does_not_block_a_later_one`.

**Result**: 224/224 committees harvested (no partial failures), 20 of
23 processed corpus designations resolved (the 3 refusals are genuine —
2 not-yet-published drafts, `"IEC/TS 63208"` vs. the catalog's own
distinct `"IEC 63208"`, correctly not force-matched). All 20 translated
to Czech, spot-checked by hand. Full pipeline rebuild: `needs_review`
366 → 349/1215. Full suite: 687 tests, all passing. App smoke-checked
live: `/`, `/procesy`, `/proces/U4` all 200, `IEC 60092-506` shows its
real description in a live search.

**`playwright` is a new dependency, deliberately scoped to
`requirements-optional.txt`, not `requirements.txt`** — nothing in the
app or the regular pipeline needs a browser, only this one harvest
script, matching the same "not needed for the documented pipeline
order" reasoning `pandas`/`duckduckgo_search` already had that file for.
The Chromium binary itself and the `sudo playwright install-deps`
system libraries are a one-time environment setup step, documented
inline in that file and in the harvester's own module docstring, not
part of any install walkthrough a partner following `PROJECT.md` would
ever need to run.

## 26. Phase 1 continued — `dvgw.de` (NEW, 2026-09-17, user-directed)

**User direction:** continue Phase 1 with `dvgw.de` (101 corpus records
— higher than §17.2's original estimate of 42, which undercounted),
now that Playwright is already set up from §25.

**Feasibility investigated live, same discipline as IEC**:
`www.dvgw.de` itself has no useful content; the real catalog is
`dvgw-regelwerk.de`. No AWS-WAF-style block here, but BOTH its search
results and its documents' detail pages are entirely client-side
JS-rendered (a plain fetch of either sees "JavaScript seems to be
disabled in your browser") — Playwright is required regardless of the
WAF question. Two further findings made this a smaller win than
`eiga.eu`/`iec.ch`:

- **Detail pages are paywalled beyond a title and one short subtitle
  line** — no real scope paragraph like EIGA or IEC gave us, confirmed
  live (`arbeitsblatt-g-100/8e3b63`: "You are currently not logged in
  as a subscriber").
- **The site's own free-text search is unreliable for exact
  designation lookup** — tested live against 7 designations (`G 260`,
  `G 1001`, `G 213`, `G 406`, `GW 129`, `G 685-1`, `ZP 4110`): **0 of 7
  appeared anywhere in their own search results**, and several
  distinct queries (`G 1001`, `G 406`) returned the *identical* generic
  top-3 hits, suggesting the search silently falls back to a fixed
  popular-documents ranking for a term it doesn't recognize rather
  than returning nothing. Trusting it would have meant either missing
  most records or risking a false match — neither acceptable.

**What DOES work, reliably, with no guessing**: DVGW's own curated
*listing* pages already carry a one-line description alongside every
entry, no detail-page visit needed — three "special topic" pages (H2
Industry/Production/Complete edition, paginated via numbered buttons
that update client-side with no URL change) and three "index" category
listings (Set of Rules for Gas, for Gas/Water, DVGW Information
bulletins — these load via infinite scroll instead, a second, different
pagination UI on the same site). New `src/tools/
harvest_dvgw_publications.py` harvests all six. **These do not cover
DVGW's full catalog**: combining all six only resolves **41 of the 101**
corpus DVGW designations — confirmed by checking coverage after each
addition (topic pages alone: 40; adding all three index listings: 41,
barely more). The other 60 are not reachable through this site without
guessing.

**Per user direction** ("build the 41 and mark the rest as requiring
review"): new `src/sites/dvgw.py` is the lightweight, network-free
consumer (same shape as `iec.py`) with `is_dvgw_norm_record()`/`dvgw:
<designation>` wired into `fetch_authoritative_metadata.py` and
`build_unified_db.py`'s `apply_authoritative_metadata()` fallback
cascade (same `_fetched_cache_entry()` discipline §25 already
established). A DVGW record whose designation isn't in the harvested
index is **not just silently left with the generic "missing
description" flag** every other unresolved record gets — it's also
recorded in a new `data/dvgw_unresolved_review_queue.json`, recomputed
from the FULL final cache at the end of every `fetch_authoritative_
metadata.py` run (not just this run's new lookups, so an already-cached
miss from a previous run still shows up even when this run skipped
re-processing it) — so it reads as "looked for, genuinely not there
on this site" rather than being indistinguishable from a record nobody
has tried yet.

**Result**: 52 designations processed (`--only-missing-description`
scope), 20 found and translated to Czech, 32 correctly recorded as
unresolved. Full pipeline rebuild: `needs_review` 349 → 333/1215. Full
suite: 702 tests, all passing. App smoke-checked live: `G 404 (M)` now
shows its real (translated) description in a live search.

## 27. Phase 1 stopped here — diminishing returns confirmed (NEW, 2026-09-17, user-directed)

**User direction:** continue Phase 1 once more; investigate whatever
domains remain. Live database breakdown of still-missing descriptions
at this point: `iso.org` 73 (confirmed blocked, §17.7), *(no URL)* 53
(not a site-fetchable problem at all), `normy.normoff.gov.sk` 34
(already attempted, §17 — genuine remaining gaps, not a new domain),
`dvgw.de` 24 (already attempted, §26), `slov-lex.sk` 20
(`slovlex.py` exists but is structurally title-only — no description
ever available from that site), `bveg.de` 14 (already flagged weak —
no designations to search by), `csnonline.agentura-cas.cz` 11 (already
attempted, §9), then five untried domains at ~9-10 records each:
`din.de`, `ptb.de`, `csagroup.org`, `sae.org`,
`standards.cencenelec.eu`; `eur-lex.europa.eu` 6 (`eurlex.py` exists,
also structurally title-only); everything else ≤5 each.

Checked the two most promising of the five untried domains live (both
returned a plain HTTP 200, unlike `cencenelec.eu` which failed to
connect at all):

- **`csagroup.org`** (10 records, all `CSA`/`CSA/ANSI` hydrogen vehicle
  fuelling standards): the store page's own search `<input>` exists in
  the DOM but stays **not visible** even after accepting the cookie
  consent banner — some other UI state (of ~50 search-related elements
  found) has to be triggered first, not identified within a
  proportionate amount of investigation for a 10-record yield.
- **`sae.org`** (10 records, `SAE J...` ground-vehicle standards): both
  a guessed detail-page URL and the site's own `/publications/search`
  endpoint returned a generic JS shell (`<noscript>` present, ~116
  lines) — no working static entry point found on a quick check.

**Decision: stop Phase 1 here.** The pattern is now consistent across
seven investigated domains (`normoff.gov.sk` succeeded cleanly; `eiga.eu`
succeeded after a real correction; `iec.ch` succeeded via a heavier
Playwright harvest; `dvgw.de` succeeded partially via curated listings;
`iso.org`, `csagroup.org`, `sae.org` all show real access friction for
what would be a small yield even if solved) — every domain with real
remaining volume is either already attempted (with genuine residual
gaps, not a new opportunity) or structurally incapable of ever
providing a description (`slov-lex.sk`/`eur-lex.europa.eu`, title-only
by design) or confirmed/strongly-suspected blocked
(`iso.org`/`csagroup.org`/`sae.org`). `din.de`/`ptb.de`/
`cencenelec.eu` were not individually checked, but no reason to expect
a different outcome given the consistent pattern above — left
genuinely untried rather than assumed, should a future session want to
check them specifically.

Corpus-wide state at the end of Phase 1's active work this session:
`needs_review` 450 → 333/1215 (over the whole Phase 1 arc:
`normoff.gov.sk`, `eiga.eu`, `iec.ch`, `dvgw.de` combined).

## 28. Corpus expansion: harvest new, URL-verified hydrogen documents — Phase A, EU legislation (NEW, 2026-09-17, user-directed)

**User feedback:** the database was reported incomplete — missing
national laws, directives, and lower-level guidance/methodologies, no
concrete title given. Separately, a colleague ran an AI model and got
"a lot of documents" not in our list; the user is rightly skeptical of
hallucination there (no list was available to cross-check). The
non-negotiable constraint for all of this work: **every document added
must be independently verifiable at a real, visitable URL** — never
guessed, never asserted on an LLM's say-so. Scoped to **EU legislation
first** this round (Czech national law and lower-level guidance/
methodologies deferred — see below for why).

### 28.1 What already existed

`src/tools/screen_eurlex.py` already screened the EUR-Lex Cellar SPARQL
endpoint for "hydrogen" in `cdm:expression_title`, diffed against every
`znacka` already in the corpus, and wrote new hits to
`data/fulltext_screening_candidates.json["EUR-Lex"]` — but never
auto-inserted them. A 2026-09-09 run had left 199 real, unconverted
candidates sitting there.

### 28.2 Hardening the screen before trusting it further

`RESULT_LIMIT = 200` had returned 199 rows — one query away from silent
truncation. Raised to 1000 (simpler than OFFSET paging at this scale)
with a runtime warning if the limit is ever hit again. Added `"RFNBO"`
(the defined EU regulatory term for renewable hydrogen) alongside
`"hydrogen"` — deliberately not a broader net of loosely-related terms.
A live re-run found the true total was 303 (0 from "RFNBO", a harmless
no-op) — confirming the old limit really had been truncating.

### 28.3 `src/tools/add_eurlex_hydrogen_acts.py` — verify live, then write real Document rows

New script, one candidate at a time:
1. Classify by CELEX type letter — only binding act types (Regulation/
   Directive/Decision, R/L/D) auto-convert; everything else (Recommen-
   dations, and non-standard-shape ids like OJ "C" series notices or
   preparatory-act ids) is logged to
   `data/eurlex_administrative_not_imported.json`, not silently
   dropped.
2. Re-diff against the **current** `database_merged_raw.json` (not the
   stale screening snapshot — the corpus had grown since normoff/eiga/
   iec/dvgw work all landed).
3. Re-fetch the title **live** via `src/sites/eurlex.py:extract()` —
   never trust the screening snapshot's title; a CELEX that no longer
   resolves is skipped and logged.
4. **Filter off-topic chemistry/administrative false positives** (added
   after the first full run — see 28.4 below).

Idempotent via its own output file (`znacka`-based diffing, no side-
channel bookkeeping field). 14 unit tests (`tests/test_add_eurlex_
hydrogen_acts.py`) cover the CELEX classification, znacka construction,
and record shape with real fixture data.

### 28.4 A real problem found on the first full run: "hydrogen" the word vs. hydrogen the energy carrier

The first full batch run (before the filter in 28.3.4 existed) added
**51** binding-type acts. Manual inspection of all 51 titles found only
**13** were genuinely about hydrogen as an energy carrier — the other
**38** were EU acts about entirely different things that happen to name
a compound containing the word "hydrogen": "hydrogen peroxide" biocide
authorisations (regulation 528/2012 — several different named product
families, renewals, refusals, administrative amendments), "potassium/
sodium hydrogen carbonate" (bicarbonate) pesticide active-substance
approvals and MRLs (regulations 1107/2009 and 396/2005), "hydrogen
cyanide" biocide approvals/derogations, a "silver-sodium-zirconium
hydrogen phosphate" biocide non-approval, a 2006 Commission cartel
decision about the hydrogen peroxide/perborate market, a 1975 customs
notice on "sodium hydrogen glutamate", and a 1981 customs ruling on a
gas chromatograph with a "hydrogen generator" accessory. None of this
is transportation- or energy-related hydrogen regulation, and none of
it belongs in this database.

Fixed by adding `OFF_TOPIC_TITLE_PATTERNS`/`is_off_topic()`: a deny-list
of the exact chemistry/administrative vocabulary found in that batch
("peroxid"/"peroxide", "biocid", "kyanovodík"/"hydrogen cyanide",
"hydrogenuhličitan"/"hydrogen carbonate"/"bicarbonate",
"hydrogenfosforečnan"/"hydrogen phosphate", "hydrogen glutamate",
customs-duty/tariff phrasing), checked against the freshly re-fetched
live title (not the stale snapshot). Verified against the same batch:
all 38 false positives now correctly excluded, all 13 genuine hydrogen-
energy acts (the Fuel Cells and Hydrogen 2 Joint Undertaking and its
predecessor/amendments, hydrogen-vehicle type-approval regulations and
their implementing/amending acts, alternative-fuels-infrastructure
delegated acts covering hydrogen refuelling, and the hydrogen-market
support mechanism's exclusion of Russian/Belarusian supply) still pass.
Excluded candidates are logged to `data/eurlex_off_topic_not_imported.
json`, not silently discarded. 8 new unit tests cover this classifier
against real titles from both sides of the split.

Re-running the full batch cleanly (300 candidates) with the filter in
place: **13 added**, 239 non-binding type, 4 already in corpus, 38
off-topic, 6 no longer resolvable live via Cellar (superseded/
consolidated CELEX ids). All 13 spot-checked: every `odkaz_hlavni` URL
returns HTTP 200 live.

### 28.5 Wiring in and rebuilding

`data/discovered_eu_hydrogen_acts.json` wired into
`build_unified_db.py` as an 8th source (`load_json()` +
`unified_db.extend()`, same pattern as `eu_transposition_targets.json`).
Full pipeline rebuild (`build_unified_db.py` → `deduplicate_db.py` →
`link_document_versions.py` → `link_document_relations_auto.py` →
`init_db.py` → `load_document_relations.py` → `load_process_layer.py`):
`database_merged_raw.json` grew from 2280 to 2293 records (exactly +13,
the expected type-filtered, off-topic-filtered, live-reverified count),
`Total Documents` in the live database now 1228. Full test suite (724
tests) and the live-database `test_search.py` integration test both
green afterward.

### 28.6 Deferred to a later round

Per direction: **Czech national law** — `screen_esbirka.py`'s e-Sbírka
SPARQL graph can't resolve a hit back to its owning act (its 100 real
candidates are mostly noise — a 1920s tariff schedule mentioning
"vodík technický" as a chemical term, unrelated fragments); and
`zakonyprolidi.cz`'s search is behind a Cloudflare "Just a moment..."
challenge that even headless Chromium (already cleared the AWS WAF
challenge for `iec.ch`, §25) could not pass on a live test. Two real
paths forward, neither resolved yet: register for e-Sbírka's official
REST API (an institutional step only the user can take), or find a
different public Czech legislative source not yet checked. **Lower-
level guidance/methodologies** (HYTEP, EHTA, MPO, ERÚ, ÚNMZ, ...) — no
single registry by nature; needs the same per-institution feasibility
investigation as the `dvgw.de`/`eiga.eu` work (§24/§26), one institution
at a time. Both treated as their own follow-up phase, not attempted
this round.

## 29. Off-topic filter, second layer — a probabilistic/LLM backstop for whatever the pattern deny-list doesn't already know (NEW, 2026-09-17, user-directed)

**User's question, after seeing §28.4's `OFF_TOPIC_TITLE_PATTERNS`:**
what happens when a new off-topic EU act appears that this exact
deny-list wasn't written for? Requested a second, probabilistic layer
scoring title relevance, with three outcomes — (a) pattern match or (b)
high off-topic score both excluded, (c) low-confidence/uncertain scores
routed to a review queue instead of guessed at either way — and asked
for an LLM-based option specifically, with everything logged.

### 29.1 Design

`assess_relevance(title, matched_keyword, celex)` in
`src/tools/add_eurlex_hydrogen_acts.py` now runs two layers in order:

1. **Pattern deny-list first** (`is_off_topic()`, unchanged from §28) —
   free, deterministic, and already validated against the real batch
   that motivated it. A match short-circuits: the LLM is never called
   for a title the pattern list already recognizes.
2. **LLM backstop** (`classify_relevance_with_llm()`) for whatever
   survives step 1 — the same `gpt-4o-mini`/`response_format=json_object`/
   `temperature=0.0` call shape `deduplicate_db.py`'s
   `deduplicate_cluster_with_llm()` already uses elsewhere in this
   pipeline, same `MAX_LLM_ATTEMPTS`/retry-with-backoff discipline. Asks
   for `{"off_topic_probability": 0-100, "reasoning": "..."}` given the
   title, matched keyword, and CELEX id — framed as "this already passed
   the binding-act-type and keyword filters; judge ONLY whether it's
   genuinely about hydrogen as an energy carrier, or a chemical/
   administrative false positive like §28.4's".

Two thresholds convert the score to a verdict, not one — so an
uncertain score is never silently resolved either way:
`HIGH_OFF_TOPIC_THRESHOLD=75` (score ≥ this → excluded, same handling
as a pattern hit), `LOW_ON_TOPIC_THRESHOLD=25` (score ≤ this → proceeds
to import), anything in between → `data/eurlex_relevance_review_queue
.json`. **A failed/unreachable LLM call is treated identically to an
uncertain score** — `classify_relevance_with_llm()` returns `None` on
exhausted retries, and `assess_relevance()` maps that to the same
`"needs_review"` verdict, never defaulting to on-topic (which would
silently readmit exactly the false-positive pattern this whole feature
exists to catch) or off-topic (which would silently discard a possibly
genuine record — the same "never guess" principle as the rest of this
script).

### 29.2 The OpenAI client — deliberately NOT `deduplicate_db.py`'s pattern

`deduplicate_db.py` calls `exit(1)` if `.openapi_key` is missing,
because it's only ever run interactively. This script runs as part of
an unattended batch (doc/PLAN.md §28.3), so
`add_eurlex_hydrogen_acts.py` loads its own client the same way but
degrades instead of crashing: `client = None` on a missing key file,
and every LLM-stage candidate then resolves to `"needs_review"` (never
silently to on-topic or off-topic) rather than the whole run aborting.

### 29.3 Logging — all three outcomes, never silently dropped

- `data/eurlex_off_topic_not_imported.json` (already existed, §28) now
  carries a `detection_method` field (`"pattern"` or `"llm"`) plus
  `llm_score`/`llm_reasoning` when applicable, so a pattern-caught and
  an LLM-caught exclusion are distinguishable after the fact.
- `data/eurlex_relevance_review_queue.json` (NEW): candidates the LLM
  scored in the uncertain middle band, or that it could not classify at
  all (client unavailable, every retry failed) — same shape as the
  off-topic log, `detection_method="llm"` or `"llm_unavailable"`.

### 29.4 Tests and verification

11 new unit tests in `tests/test_add_eurlex_hydrogen_acts.py`
(`ClassifyRelevanceWithLlmTestCase`, `AssessRelevanceTestCase`): the
OpenAI client mocked the same way `test_deduplicate_db.py` already
mocks `deduplicate_db.client` — no real API call in the test suite.
Cover: unconfigured client → `None`; a valid response parsed; an
invalid score and an API exception each retried up to
`MAX_LLM_ATTEMPTS` before giving up; a pattern hit short-circuits
without ever calling the injected LLM; high/low/middle scores map to
the three verdicts; an unavailable LLM maps to `"needs_review"`, not a
guess; and the threshold boundaries themselves resolve to a decided
verdict, not `"needs_review"`. Live smoke-tested against the real API
(not part of the automated suite) with one synthetic off-topic title
outside the pattern list's vocabulary (a hypothetical "hydrogel-based
crop pesticide" act) and one genuine hydrogen-refuelling-infrastructure
title — scored 90 and 0 respectively, both landing on the correct side
of the thresholds. Full test suite (735 tests) stays green.

Re-running the full §28 batch was not necessary: all 38 off-topic
candidates in that specific batch were already caught by the pattern
layer alone, so the LLM path was never reached for any of them in that
run — this second layer is insurance for a future run's not-yet-seen
false-positive vocabulary, not a correction to §28's already-verified
13-record result.

## 30. Corpus expansion, continued — Czech national law (NEW, 2026-09-17, user-directed)

**User instruction:** continue Phase 1 with the item deferred at the
end of §28 — Czech national law discovery, previously blocked on two
real walls: e-Sbírka's own SPARQL graph "doesn't reliably carry a
scrapeable back-link to its owning act" (§28's own words, quoting
`screen_esbirka.py`'s docstring) and `zakonyprolidi.cz`'s search being
Cloudflare-blocked. A live re-investigation this round found both walls
were narrower than they looked.

### 30.1 The technical unlock: a reverse SPARQL hop resolves fragment → act

`screen_esbirka.py`'s full-text hits are `právní-akt-fragment`/
`-binární-soubor`/`-metadata` nodes. Querying a hit's own (forward)
properties really does dead-end, exactly as documented — but a live
query in the OTHER direction doesn't: `SELECT ?s WHERE { ?s
<.../pojem/obsahuje-fragment> <fragment-uri> . }` returns a node whose
OWN URI already has the shape `.../eli/cz/sb/{year}/{number}/{date}/
dokument/...` — year and number sitting directly in the URI path, no
further vocabulary knowledge needed. A `právní-akt-binární-soubor` hit
needs one extra hop first (`.../pojem/má-binární-soubor` to its owning
fragment) then the same reverse-fragment hop. Verified against several
real hits from the existing 100-candidate file, including a genuinely
new relevant one (a "binární-soubor" node → its fragment → an
`eli/cz/sb/2015/294/...` URI). A `právní-akt-metadata` node has no such
link at all (confirmed empirically: neither a forward nor reverse query
found anything) and stays permanently unresolved by this method — a
real, disclosed residual, not silently worked around.

`src/tools/add_esbirka_hydrogen_acts.py`'s `resolve_znacka_for_uri()`
implements exactly this: one hop for a fragment node, two for a binary-
soubor node, `None` (never guessed) for metadata or an orphaned node the
reverse query comes back empty for.

### 30.2 A second, independent false positive: "vodítko" isn't "vodík"

Live-checking the existing 100-candidate file's snippets by hand found
~9 hits were "vodítko"/"vodítka"/"vodítek" (elevator/lift guide rails)
or "vodicí" (guide-, as in "vodicí lano") — words sharing `screen_esbirka
.py`'s old 4-character `"vodí*"` wildcard prefix with "vodík" but
meaning something else entirely. Fixed at the source: `HYDROGEN_KEYWORDS
= ["vodík*"]` (one more character; still covers every inflected form —
vodík/vodíku/vodíkem/vodíková/vodíkový/vodíkových/vodíkovým/vodíky all
share "vodík" as their first 5 characters, while the 5th letter alone
already excludes the guide-rail words). The EXISTING candidates file was
collected under the old keyword and still carries that noise (fixing
the constant doesn't retroactively clean a file `screen_esbirka.py`
only ever appends to), so `add_esbirka_hydrogen_acts.py` re-checks
defensively with a fixed `\bvodík` regex (`is_actual_hydrogen_mention`)
before doing anything else with a candidate — cheaper than a SPARQL
round-trip, so this check runs first.

### 30.3 Off-topic classification works on the matched snippet, not the document title — the reverse of §28/§29

For EU acts, an off-topic TITLE was itself the signal ("...Hydrogen
Peroxide Biocidal Product..."). Here, the matched snippet is typically
one paragraph or table cell buried inside a much longer, topically
unrelated act — a 1930s customs-tariff schedule, a decree implementing
road-traffic rules — so the document's own title usually says nothing
about hydrogen at all, on-topic or off, while the matched fragment
always does. Classification therefore runs on the snippet
(`data/fulltext_screening_candidates.json`'s own `snippet` field,
HTML-stripped — many hits are literal `<table>` markup from old tariff
schedules), never the act's title.

Manually classifying all 100 pre-existing candidates found: 26 unique
acts total, of which 24 were customs-tariff schedules or 1920s-1950s
bilateral trade/rail treaties (list "vodík" only as one commodity among
many in a tariff table) or old hydrogen-peroxide transport/biocide rules
("peroxyd(u)/superoxyd(u) vodíku" — pre-1957-orthographic-reform
spelling), and exactly 2 were genuinely on-topic: traffic-sign 409
"Čerpací stanice vodíku" (hydrogen filling station) in `294/2015 Sb.`'s
annex 7, and its `205/2025 Sb.` amendment updating the same sign.

Same two-layer architecture as §29's EU version — a deterministic
pattern deny-list (`OFF_TOPIC_SNIPPET_PATTERNS`: celní sazebník/sazby,
old bilateral trade treaties, "peroxyd(u)/superoxyd(u) vodíku") first,
then an LLM backstop (`classify_relevance_with_llm`/`assess_relevance`,
own client/prompt, same `HIGH_OFF_TOPIC_THRESHOLD`/
`LOW_ON_TOPIC_THRESHOLD`/needs-review-band contract) for whatever the
patterns don't catch. A live full-batch run: the pattern layer caught
most of the peroxide/customs vocabulary directly; the LLM correctly
scored one genuinely ambiguous case ("stlačený kyslík...vodíku" — a
compressed-gas purity threshold, arguably industrial-gas safety rather
than hydrogen energy specifically) into the needs-review band rather
than guessing either way — the same kind of judgment call the design is
built to defer to a human on.

### 30.4 The rest of the pipeline

`typ_dokumentu` reuses `build_unified_db.py:classify_law_document_typ()`
rather than reinventing it — but that function's "Vyhláška"/"Nařízení
vlády" patterns are anchored at the string's start (`^\s*vyhlá...`),
and zakonyprolidi.cz's og:title is "294/2015 Sb. Vyhláška, kterou..." —
title-first, `znacka`-prefixed. Passed raw, every Vyhláška/Nařízení-
vlády record would misclassify as `""` (unclear). Fixed with
`strip_leading_znacka()`, stripping that prefix before classifying —
found and fixed BEFORE it could silently corrupt a downstream
classifier the new source was never written for, same discipline as
§28's title-refetch requirement. `odkaz_hlavni` is the direct
zakonyprolidi.cz per-document URL (`.../cs/{year}-{number}`) — the
SEARCH endpoint is Cloudflare-blocked (§28's own finding), but a direct
document URL, per `src/sites/zakonyprolidi.py`'s own docstring, is not
and was never re-tested as blocked; confirmed again live this round.
`gestor` is left `[]` — no institution lookup available from either
e-Sbírka's LOD graph or zakonyprolidi.cz for a freshly-discovered act.

27 new unit tests (`tests/test_add_esbirka_hydrogen_acts.py`), all
network/API calls mocked. Full pipeline rebuild:
`database_merged_raw.json` 2293 → 2295 (exactly +2, matching the two
live-verified records), live `Total Documents` 1228 → 1230. Full test
suite (762 tests) and the live-database `test_search.py` integration
test both green afterward. Both new records' `odkaz_hlavni` URLs
confirmed HTTP 200 live.

### 30.5 What's still not covered, left as a disclosed residual

`právní-akt-metadata` hits (1 in the existing batch) and the small
number of fragment/binary-soubor hits whose reverse query comes back
empty (2 in this batch) stay in `data/esbirka_unresolved_not_imported
.json` — genuinely unresolvable by this method, not pursued further
this round (a small, bounded residual, same "diminishing returns"
judgment as §27's IEC/DVGW stopping point). e-Sbírka's own registered
REST API (an institutional Ministry-of-Interior data-box registration)
remains the eventual, more complete path if ever obtained — unchanged
from §28's assessment.
