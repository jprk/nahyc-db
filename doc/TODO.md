# A list of things to consider for H2DB project

## 001 - How well does the project meet its requirements?


  *"strukturovaným... zdrojem informací" (structured)*

  Solid. Clean relational schema, 1272 documents, proper versioning/lifecycle state (R1.5 PASS), M:N keyword indexing (R1.8 PASS). One real bug though: Document.id 117 and 122 are exact duplicates — same Slovak law, same
  title, same URL — both with NULL identifier, so the UNIQUE constraint never saw them. This directly undercuts R1.1's "enforce strict record uniqueness" claim. Trivial to fix (merge two rows), but it's live, not
  theoretical.

  *"přístupným... pro všechny zainteresované subjekty" (accessible to all stakeholders)*

  The UI itself is solid — responsive, combined full-text+filter search, CSV/JSON/XML export, all PASS. But I checked the production URL your own project docs reference (doc/konsolidace/Konsolidace-DB-popis.md: "Nad V01 běží
  produkční Flask aplikace (https://nahyc.fel.zcu.cz/h2db/)") — it currently returns HTTP 404 (the bare domain works, /h2db/ doesn't). No CI/deploy config exists in the repo either. Right now I can't confirm this is
  actually reachable by "all interested parties" outside a local dev instance — worth checking with whoever manages that deployment.

  *"klíčové národní i mezinárodní regulační předpisy a normy" (national + international)*

  Present and broad — CZ, SK, EU, and international (ISO/IEC/DIN/etc.) all represented, 3-tier jurisdiction classification exists and mostly works. Gap: 152 documents (12%) have no jurisdiction assigned at all (NULL or
  'neurčeno') — a data-completion task, not a design flaw.

  *"výstavbou, instalací a provozem" (construction, installation, operation)*

  Covered by the document corpus broadly. Worth knowing: the process model (V02, nodes U1-U7) is explicitly scoped to "předrealizační procesy" (pre-realization) by the project's own title and design docs — it models the path
  to getting authorized to build/install/operate, not day-to-day operational-phase workflows. That's a documented, deliberate scope choice already baked into the project's own naming, not something I'm flagging as new.

  *"průběžně aktualizována na základě legislativních změn" (continuously updated)*

  This is the clearest gap. Atr this moment there is no crontab, no systemd timer, no CI workflow anywhere. Every single update — including the entire session's corpus-expansion arc — has been a human explicitly typing "continue
  with Phase 1." The pipeline itself is genuinely good at incremental updates (proven repeatedly this session), but "průběžně" (ongoing/continuous) implies some unattended cadence that doesn't exist yet. Worth deciding
  explicitly whether that's in scope for this project phase.

  *"Část konsolidovaných dat... přístupné přes služby... třetích stran" (paid third-party access for norms)*

  Implemented. Norma-type documents correctly show "Plný text nedostupný 🔒" with a copyright/paywall tooltip, link out to the real external source, and — a detail most implementations miss — bulk export correctly
  excludes the restricted fields too.

  Two more concrete coverage gaps worth knowing about

  - EU→national transposition linking: only 6 IMPLEMENTS edges exist against 13 Směrnice EU documents in the corpus — thin relative to what's likely really there.
  - ISO↔national-standard linking: only ~25 of ~312 candidate ISO-derived national adoptions (ČSN/STN/DIN EN ISO...) are actually linked via ADOPTS — about 8%. The linker (link_document_relations_auto.py) works correctly
    where it's run; it just hasn't been run to exhaustion against the recently-expanded corpus.

  Bottom line: the architecture and mechanisms genuinely deliver on the stated design (R2.x/R3.x/R4.1 all clean PASS), but there's one live data bug, two link-coverage gaps that are cheap to improve by re-running an existing
  tool, and one real, unaddressed gap between "průběžně aktualizována" and the current fully-manual reality. Nothing here needs a redesign — I'd treat the duplicate-record fix and a re-run of link_document_relations_auto.py
  as the two cheapest, highest-value next steps if you want me to act on any of this.

## 002 - Possible further steps (2026-09-18 20:17)

What's left open:

  1. 152 documents with no jurisdiction assigned (NULL/'neurčeno') — a data-completion task, not yet touched.
  2. No automation for "průběžně aktualizována" — no cron/CI, every update this session has been manual. Bigger undertaking, needs a scoping decision from you (and per last turn's memory note, must also invoke every
     backfill_*.py, not just the 3 core pipeline steps).
  3. 27 secondary/incidental EU-act references left unresolved from §39 — would need per-citation context work to close properly.
  4. Slovak (SK) law discovery — you postponed this earlier in the session.
  5. Production URL returns 404 (https://nahyc.fel.zcu.cz/h2db/) — flagged in TODO.md but outside what I can fix; that's a deployment/infra question for whoever manages that server.

No single unified plan ties these together — they're independent backlog items.


## 003 - Rozpracované feature větve a worktrees (2026-10-24)

Pracovní konvence: každý krok se dělá na vlastní feature větvi v samostatném
worktree (`git worktree add ../nahyc-h2db-<název> -b feature/<název> automation`).
Hlavní strom (`/home/laborator/DEVEL/nahyc-h2db`, větev `automation`) zůstává
beze změny; obsahuje rozpracovanou reorganizaci, kterou nemíchat s feature větvemi.

| Worktree | Větev | Základ | Stav |
|---|---|---|---|
| `../nahyc-h2db-wire-agentic` | `feature/wire-agentic-candidates` | `automation` @ `13db9b1` | commit `b3a2b5d`, nezmergováno, nepushnuto |
| `../nahyc-h2db-reorg` | `reorganizace` | `master` @ `0f45c45` | commit `82b8e45` (přesun `tools/`, `db/`, `documents/`, `text/` do `src/`, `doc/`, `tests/`; + `CLAUDE.md`, `TEXT_STYLE.md`), nezmergováno, nepushnuto |
| `../nahyc-h2db-fulltext-extract` | `feature/fulltext-extract` | `master` @ `0f45c45` | extraktor čistého textu (issue #2), commit lokální, nepushnuto, bez napojení na aplikaci |

### `feature/wire-agentic-candidates` — krok 1 z přehledu nedodělků
- Co: `build_unified_db.py` nově načítá `data/discovered_agentic_candidates.json`
  (funkce `load_agentic_candidates()`, blok č. 14; chybějící soubor = prázdný seznam,
  poškozený soubor se ohlásí a přeskočí). Zavírá `doc/AUTOMATION.md` §6.3 / §8 bod 2.
- Testy: 4 nové v `tests/test_build_unified_db.py` (82/82 OK ve worktree);
  popis doplněn v `tests/0README.md`.
- Neověřeno: celá sada testů ve worktree, reálný průchod přestavby (soubor
  kandidátů zatím neexistuje, nikdy se nespustil `run_agentic_pipeline.py --apply`).
- Zbývá po mergi: upravit `doc/AUTOMATION.md` §6.3/§8 (v hlavním stromu je
  nesledovaný, ve worktree proto neexistuje) a případně `src/agentic/0README.md`.

### Další kroky v pořadí (z přehledu `doc/` ze 2026-10-23)
2. Rozhodnutí zadavatele k R1.9 (plánovač vs. úprava znění požadavku).
3. Aktualizace hlavičky `doc/PLAN.md` a vyčištění tohoto souboru.
4. Screenery VeKLEP a Slov-Lex legislatívny proces (`data/monitored_sources.json`).

### Rozdělení změn (2026-10-24)
Původně ležela reorganizace necommitovaná v hlavním stromu na větvi `automation`.
Rozdělení: agentní práce commitnuta na `automation` (`12ce41b`), reorganizace
přesunuta na větev `reorganizace` (od `master`). Hlavní strom proto už nemá
`CLAUDE.md`, `TEXT_STYLE.md` ani kořenový `0README.md` — jsou jen na `reorganizace`.
Dvě `.xlsx` v `data/*/raw/` mají na disku zkomolené názvy (mojibake); obsah je
shodný s verzovanými originály, proto se nezařadily — kopie lze smazat.
`feature/wire-agentic-candidates` je odvozena z `13db9b1`, před mergem do
`automation` je třeba ji rebasovat na `12ce41b`.

### Živá DB `h2regdocs` — schéma §42 doplněno (2026-10-24)
Porovnání s `h2regdocs_test` ukázalo jediný rozdíl: chyběly `User`, `ReviewItem`,
`AuditLog`. Po záloze (`backups/h2regdocs_20261024_111830.sql.gz`, mimo git) byly
vytvořeny třemi `CREATE TABLE` z `Konsolidace-DB-schema.sql`; data (1462 `Document`)
nedotčena, opětovné porovnání bez rozdílů. Zbývá založit editorské účty
(`src/db/dbuser_add.py`) — zadává se heslo, dělá uživatel.
