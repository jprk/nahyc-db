# Adresář /doc

Dokumentace projektu a zdrojové podklady (V01–V03), ze kterých vychází
konsolidované databázové schéma v `doc/konsolidace/` (viz jeho vlastní
`0README.md`).

* `NAHYC DP004 V01 - Databáze regulačních předpisů.docx` — metodika a popis databáze regulačních předpisů (výsledek DP004/V01).
* `NAHYC DP004 V02 - Popis procesů.docx` — popis předrealizačních procesních uzlů U1–U7 (branže, kroky, vstupy, výstupy, subjekty, problémy) + 59položková bibliografie. Zdroj pro vrstvu B konsolidovaného schématu — viz `doc/PLAN.md` Krok 3a a `src/tools/parse_v02_processes.py`.
* `NAHYC DP004 V03 - Popis regulatorního a procesního rámce.docx` — klasifikace vodíkových instalací, institucionální rámec, návrh vrstvy D (compliance pathway: `technology_type`, `project_criterion`, `node_activation_rule`, `use_case_scenario`). Zatím jen prozkoumáno, ne zpracováno — Krok 3b v `doc/PLAN.md` je odložen (formalizace aktivačních pravidel je dle vlastního textu V03 nedořešená metodická otázka).
* `PLAN.md` — živý plán konsolidace databáze a automatizace (viz jeho vlastní obsah pro aktuální stav).
* `similarity_analysis.md` — generovaný report `src/tools/analyze_similarities.py` (šedá zóna podobnosti při deduplikaci).
* `konsolidace/` — konsolidované databázové schéma, viz jeho vlastní `0README.md`.
* `automation_proposal/` — externí návrh automatizace (Gemini research-agent transkript), reconciliován v `PLAN.md` §3.
