# Adresář /app/templates

Tento adresář obsahuje Jinja2 HTML šablony pro vykreslování uživatelského rozhraní webové aplikace (např. `index.html`, `base.html`).

**doc/PLAN.md §42 (2026-09-18, uživatelské zadání)**: podadresář `admin/` — šablony pro editorský blueprint `app/admin.py` (přihlášení, seznam položek k revizi, návrh opravy, posouzení návrhu jiným editorem, auditní log). Všechny `{% extends 'base.html' %}`, žádný nový frontend framework — jen nové sdílené třídy v `style.css` (`admin-card`, `admin-form-group`, `admin-table`, `flash*`, `diff-old`/`diff-new`). `base.html` navíc dostal blok pro `get_flashed_messages()` (dřív nepoužito nikde jinde v aplikaci) a odkaz "Editor" v navigaci.


**GitHub issue #2 (2026-10-25)**: `fulltext.html` — čtení textu předpisu přímo v aplikaci (`/dokument/<slug>/text`). Vypisuje HTML z `src/tools/extract_fulltext.py` bez escapování (`|safe`) — jediné takové místo v aplikaci, bezpečné jen díky uzavřené slovní zásobě extraktoru (bez odkazů, skriptů a atributů). Tlačítko „Číst text“ je v `index.html` a `document.html`, „Stažená kopie“ zůstává jako stažení souboru.

**doc/MPO_PRIPOMINKY.md, krok 3 (2026-11-19)**: `admin/drafts_list.html` (seznam připravovaných dokumentů, návrhy čekající na potvrzení, naposledy potvrzené změny) a `admin/draft_detail.html` (formulář převodu návrhu na vyhlášený předpis, potvrzení nebo stažení návrhu, historie) pro `app/drafts_admin.py`. `document.html` ukazuje v metadatech „Poslední kontrola stavu“ (datum a zdroj, `Document.status_checked_*`), vazbu `ENACTED_AS` („návrh vyhlášen jako“ / „vyhlášené znění návrhu“) a přihlášenému editorovi u připravovaného dokumentu odkaz na převod; `admin/review_list.html` odkaz na připravované dokumenty.
