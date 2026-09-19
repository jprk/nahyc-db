# Adresář /src/agentic

Implementace doc/PLAN.md §3's agentic architektury pro automatizované
aktualizace databáze — LangGraph `StateGraph` (`langgraph==1.2.11`,
`requirements.txt`), postavená na větvi `automation` (doc/PLAN.md §45,
2026-09-19, uživatelské zadání). **Vědomě obchází dřívější zamítnutí této
architektury v doc/PLAN.md §5** ("harden existing scripts only... No
LangGraph adoption") — výslovná instrukce uživatele pro tuto větev,
neplatí pro `master`.

CLI vstupní bod je `src/tools/run_agentic_pipeline.py` (přehled tamtéž
v `src/tools/0README.md`), ne tento adresář — moduly zde jsou čistá
knihovna, žádný z nich nemá `if __name__ == "__main__":`.

## Pipeline (`graph.py`)

Parse → Extract → Verify → (opakuj do `MAX_VERIFICATION_ATTEMPTS=3`
| escalate) → Research (podmíněně) → Reconcile → (escalate na
`"ambiguous"` | konec). Každá závislost na reálném I/O (fetch, LLM
volání, DB spojení) je do `build_graph()` injektována jako keyword s
výchozí hodnotou — testy (`tests/test_agentic_graph.py`) nahrazují
fake implementacemi, žádné reálné volání.

## Přehled modulů

* `state.py` - `PipelineState`/`Candidate` (TypedDict), `initial_state()`,
  `MAX_VERIFICATION_ATTEMPTS`.
* `parser.py` - Parser Agent. Přednost už staženému souboru z
  `fetch_fulltext.py`'s manifestu (`data/fulltext_manifest.json`, hledáno
  podle shody `url` pole v hodnotě záznamu, ne podle klíče — kandidát ze
  screeningu nemá `zdroj_dat`/`znacka` potřebné pro sestavení klíče), jinak
  živý fetch. `pdfplumber` pro PDF (stejný vzor jako
  `src/sites/eiga.py:_extract_pdf_lead()`), `BeautifulSoup` pro HTML.
  Záměrně NENÍ VLM/layout model (LlamaParse/Docling/Marker), jak §3.2
  původně navrhoval — reálný vstup (digitálně nativní PDF/HTML, ne sken)
  tuto vrstvu nepotřebuje.
* `extraction.py` - Extraction Agent. Klient/retry/`response_format`
  vzor zkopírován z `src/tools/add_eurlex_hydrogen_acts.py`'s
  `classify_relevance_with_llm()` — `client=None` bez `.openapi_key`,
  nikdy `exit(1)`. Schéma vyžaduje `verification_evidence` (pole
  doslovných citací) — bez něj/s prázdným polem Verification Agent
  vždy selže "zavřeně". `extract_with_retry_feedback()` připojí
  odmítnuté citace z předchozího pokusu do promptu (§3.3 krok 3).
* `verification.py` - Verification Agent, DETERMINISTICKÝ (ne druhé
  LLM volání). `verify_evidence()` kontroluje každou citaci
  proti `normalize_text()`-normalizovanému zdrojovému textu — přesně ta
  brána, kterou žádný z dřívějších enrichment skriptů (`enrich_eu_laws.py`
  aj.) nemá.
* `research.py` - Research Agent, podmíněný (`needs_research()`) —
  spustí se jen když `nazev`/`gestor` chybí i po verifikaci. Znovupoužívá
  `src/sites/eurlex.py`'s `extract()`/`fetch_responsible_gestor()`
  (skutečné strukturované EUR-Lex Cellar dotazy), ne obecné
  webové hledání jako `search_agent.py`. Funguje jen pro EUR-Lex
  zdrojové URL — pro Slov-Lex/e-Sbírka kandidáty vrátí `None`/beze změny.
* `reconciliation.py` - Reconciliation Agent. Přesná shoda `identifier`
  (přes znovupoužité `src/tools/link_document_relations_auto.digit_core()`)
  první, pak heuristický `title_overlap_score()` (Jaccard přes slova —
  poctivě označeno jako heuristika, NE embeddingová sémantická podobnost,
  §3.2 zmiňuje "sémantický fallback" obecně). Nikdy neslučuje — jen
  `"new"`/`"existing"`/`"ambiguous"`.
* `graph.py` - `build_graph()`/`run_candidate()` — samotné LangGraph
  zapojení uzlů a podmíněných hran popsané výše.

## Co §3 navrhoval a nebylo (zatím) postaveno

* **`hydrogen_specifics`/`legal_relationships` schéma** (§3.4) — beze
  změny, mimo rozsah této dávky (schema migrace, ne agentní logika).
* **Skutečný admin-UI pohled na `data/agentic_review_queue.json`** —
  destinace human-in-the-loop existuje jen jako soubor, ne jako obrazovka
  v `app/admin.py`'s review workflow (doc/PLAN.md §42). Přirozený,
  ale samostatný navazující krok — `ReviewItem`/`app/admin.py` očekává
  existující `document_id`, zatímco eskalovaný agentic kandidát ještě
  žádný `Document` řádek nemá.
* **Research Agent pro Slov-Lex/e-Sbírka** — jen EUR-Lex má dnes reálný
  strukturovaný zdroj (`sites.eurlex`) pro doplnění chybějících polí.
