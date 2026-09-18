-- ============================================================
-- NAHYC DP004 — Konsolidované schéma databáze (MariaDB 11.x)
-- Regulační předpisy (V01) + procesní uzly U1–U7 (V02)
-- + klasifikace a compliance (V03)
--
-- Migrace je ADITIVNÍ: části A jsou ALTERy nad produkčními
-- tabulkami V01, části B–D jsou nové tabulky.
-- Pořadí příkazů respektuje závislosti cizích klíčů.
--
-- Poznámka k přenositelnosti (SQLite pro lokální vývoj):
-- ENUM nahradit VARCHAR + CHECK, AUTO_INCREMENT → AUTOINCREMENT,
-- ENGINE/CHARSET klauzule vypustit.
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- VRSTVA A — rozšíření tabulek V01 (aditivní ALTERy)
-- Předpoklad: tabulky Document, DocumentType, DocumentSource,
-- Keyword, DocumentKeyword, DocumentVersion existují dle V01.
-- ────────────────────────────────────────────────────────────

ALTER TABLE Document
  ADD COLUMN identifier VARCHAR(100) NULL,
  ADD CONSTRAINT uq_document_identifier UNIQUE (identifier);

ALTER TABLE DocumentSource
  ADD COLUMN institution_type VARCHAR(50) NULL,
  ADD COLUMN jurisdiction VARCHAR(20) NULL;

ALTER TABLE DocumentVersion
  ADD COLUMN is_current BOOLEAN NOT NULL DEFAULT FALSE;

-- Krok 2 dodatek, 2026-09-09: jurisdikce na úrovni dokumentu (STN/DIN/ČSN
-- národní adopce téže EN/ISO normy nejsou zaměnitelné) — DocumentSource.
-- jurisdiction toto nemůže nést, protože 95 % záznamů (normy) sdílí
-- prázdný gestor a spadlo by tak do jednoho společného zdroje. Viz
-- doc/PLAN.md Krok 2.
ALTER TABLE Document
  ADD COLUMN jurisdikce VARCHAR(20) NULL;

-- doc/REQUIREMENTS.md R1.2 dodatek, 2026-09-11: `jurisdikce` samo o sobě
-- je konkrétní hodnota (STN/DIN/ČSN národní kód, "EU", "mezinárodní",
-- "neurčeno") a slouží jako veto proti slučování cizích národních adopcí
-- téže EN/ISO normy — to zůstává beze změny. R1.2 ale požaduje explicitní
-- zařazení KAŽDÉHO dokumentu do jedné ze TŘÍ úrovní: mezinárodní / EU /
-- národní — "národní" znamená SKUTEČNÝ konkrétní stát (CZ, DE, SK, US,
-- CA, FR, UK, budoucí PL, ...), ne jednu vymyšlenou hodnotu "národní"
-- nahrazující ho. `jurisdikce_uroven` je GENERATED (virtuální, vždy
-- synchronní s `jurisdikce`, žádná zvláštní udržovací logika v
-- `init_db.py`) — libovolný BUDOUCÍ konkrétní stát automaticky spadne
-- do "národní" bez zásahu do kódu. `NULL`/`"neurčeno"` (184 dokumentů,
-- 2026-09-11) zůstává čestně NULL, ne odhadnuto na některou ze tří
-- úrovní — viz doc/PLAN.md §6.
ALTER TABLE Document
  ADD COLUMN jurisdikce_uroven ENUM('mezinárodní','EU','národní')
    GENERATED ALWAYS AS (
      CASE
        WHEN jurisdikce = 'mezinárodní' THEN 'mezinárodní'
        WHEN jurisdikce = 'EU' THEN 'EU'
        WHEN jurisdikce IS NULL OR jurisdikce = 'neurčeno' THEN NULL
        ELSE 'národní'
      END
    ) VIRTUAL;

-- Krok 1 follow-up #16 dodatek, 2026-09-11: řádná verzní historie normy
-- (základní vydání + novela/oprava, např. "STN EN 13445-2" -> "+A1")
-- namísto dvou nesouvisejících Document řádků se stejným názvem.
-- `version` (V01) je jen neprůhledné pořadové číslo — chybí místo pro
-- skutečné, citovatelné označení vydání (řetězec značky té konkrétní
-- edice, např. "STN EN 13445-2+A1/ - 2024.02") a jeho vlastní datum
-- platnosti. Populuje `src/tools/link_document_versions.py`, viz
-- doc/PLAN.md Krok 1 follow-up #16.
ALTER TABLE DocumentVersion
  ADD COLUMN edition_label  VARCHAR(200) NULL,
  ADD COLUMN effective_date VARCHAR(200) NULL;

-- Zákon novelizovaný JINÝM, samostatně číslovaným zákonem (na rozdíl od
-- normy, kde amendment sdílí číslo se základní normou a je tedy jen další
-- DocumentVersion téhož Document) zůstává navždy samostatný, citovatelný
-- Document řádek — vlastní `identifier` (číslo zákona), vlastní jméno.
-- Vztah mezi novelizujícím a novelizovaným zákonem se eviduje zde, NE
-- jako verze (reálný příklad z korpusu: "426/2021 Sb." AMENDS
-- "266/1994 Sb." — zákon o dráhách). Pokud korpus někdy získá "úplné
-- znění" (konsolidovaný přetisk téhož čísla zákona po zapracování
-- novel), TO by naopak patřilo do DocumentVersion (stejný `identifier`,
-- nové vydání) — ne sem. Populuje
-- `src/tools/load_document_relations.py` z ručně kurátorovaného
-- `data/document_relations.json` (podobný princip jako
-- `data/v03_layer_d_draft.json` — vyžaduje lidský úsudek, ne
-- automatické dolování z celého korpusu).
CREATE TABLE document_relation (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  from_document_id INT NOT NULL,  -- novelizující/vztahující se dokument
  to_document_id   INT NOT NULL,  -- dokument, ke kterému se vztahuje
  relation_type    ENUM('AMENDS','REPEALS','IMPLEMENTS','CONSOLIDATES','ADOPTS') NOT NULL,
  note             VARCHAR(500) NULL,
  CONSTRAINT fk_drel_from FOREIGN KEY (from_document_id) REFERENCES Document(id) ON DELETE CASCADE,
  CONSTRAINT fk_drel_to   FOREIGN KEY (to_document_id)   REFERENCES Document(id) ON DELETE CASCADE,
  CONSTRAINT uq_drel UNIQUE (from_document_id, to_document_id, relation_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

-- doc/REQUIREMENTS.md R1.3/R1.4 dodatek, 2026-09-11 (viz doc/PLAN.md §6):
-- `ADOPTS` doplněno do `relation_type` — národní (nebo EU) adopce
-- mezinárodní/EU normy (from_document_id) ADOPTS svůj mezinárodní/EU
-- původ (to_document_id), např. "STN EN ISO 11114-4" ADOPTS "ISO
-- 11114-4" — přesně vztah, který R1.4 žádá ("linking an ISO standard to
-- its ČSN EN ISO counterpart"). `IMPLEMENTS` (existující od Kroku 1
-- follow-up #16, dosud nepoužité) je pro R1.3 (národní zákon
-- transponující konkrétní směrnici/nařízení EU) — obojí nově plní
-- `src/tools/link_document_relations_auto.py`, mechanicky, nad
-- `data/database_merged_deduplicated.json`; `src/tools/
-- load_document_relations.py` nyní načítá jak ručně kurátorovaný
-- `data/document_relations.json`, tak automaticky vygenerovaný
-- `data/document_relations_auto.json`.

-- doc/REQUIREMENTS.md R1.5 dodatek, 2026-09-11 (viz doc/PLAN.md §6):
-- `is_current` (V01) je jen binární "je toto nejnovější verze", ne
-- explicitní životní stav, jak R1.5 žádá ("active, superseded, draft").
-- `lifecycle_state` NENÍ GENERATED (na rozdíl od `jurisdikce_uroven` výše)
-- — na rozdíl od `jurisdikce` (pár řízených hodnot) je zdrojový text
-- (volné pole `platnost`, promítnuté i do `effective_date` u verzovaných
-- záznamů) nestrukturovaný vícejazyčný text; klasifikace
-- (`classify_lifecycle_state()` v `src/tools/init_db.py`, pokryto testy)
-- proto běží v Pythonu při importu, stejně jako `resolve_document_type`
-- apod. `is_current = FALSE` -> vždy `'superseded'` (nahrazená verze,
-- bez ohledu na svůj vlastní tehdejší `platnost` text); `is_current =
-- TRUE` a `platnost`/`effective_date` obsahuje skutečný draft/work-item
-- marker ("Entwurf"/"Návrh", "Arbeitsdokument"/"pracovný dokument",
-- "PWI") -> `'draft'`; jinak `'active'`. Reálné markery ověřeny přímo v
-- korpusu (2026-09-11): 64 záznamů s "Entwurf-Návrh"/"Arbeitsdokument"/
-- "PWI" apod.
ALTER TABLE DocumentVersion
  ADD COLUMN lifecycle_state ENUM('active','superseded','draft')
    NOT NULL DEFAULT 'active';

-- doc/REQUIREMENTS.md R1.7/R4.1 dodatek, 2026-09-11 (viz doc/PLAN.md §6):
-- `Document.file_path` (V01) existoval, ale nikdy nebyl plněn — R1.7
-- žádá, aby metadata skutečně zahrnovala file paths. Naplňuje
-- `src/tools/init_db.py`'s `resolve_file_path()` z
-- `data/fulltext_manifest.json` (buduje `src/tools/fetch_fulltext.py`) —
-- tedy jen skutečně stažené, lokálně cachované plné texty. R4.1 zároveň
-- žádá vynucené rozlišení "metadata vždy veřejná / plný text chráněných
-- (placených) dokumentů přístup omezen" — `fetch_fulltext.py` už dnes
-- stahuje výhradně zákony (`NORM_SOURCES` normy nikdy nestahuje), takže
-- `file_path` je fakticky vždy prázdné u norem, ale to samo o sobě není
-- vynucující MECHANISMUS, jen náhodný důsledek. `DocumentType.
-- restricted_fulltext` je proto explicitní, strukturální příznak (typ
-- `"Norma"` -> TRUE, vše ostatní -> FALSE, `is_restricted_document_type()`
-- v `init_db.py`) — Flask vrstva (`app/app.py`) jej kontroluje PŘED
-- vydáním souboru přes novou routu `/fulltext/<id>`, nezávisle na tom,
-- zda `file_path` je vyplněné, takže pravidlo platí i kdyby se logika
-- plnění `file_path` v budoucnu změnila.
ALTER TABLE DocumentType
  ADD COLUMN restricted_fulltext BOOLEAN NOT NULL DEFAULT FALSE;

-- Uživatelský nález, 2026-09-11: export (R2.5) odhalil záznamy s
-- nesmyslným titulkem a/nebo chybějícím popisem — např. `znacka` "CEN/TC
-- 326 Natural Gas Vehicles" + `nazev_cz` "- Fuelling and Operation"
-- (jeden zalomený řádek zdrojové PDF tabulky rozdělený `parse_sinay_
-- normy.py`'s souřadnicovou rekonstrukcí do špatných sloupců). Namísto
-- tichého zobrazení/exportu takového záznamu se PŘI IMPORTU (`src/tools/
-- init_db.py`'s `detect_data_quality_issues()`) označí k ruční kontrole —
-- nikdy se needhaduje/needopraví automaticky. `app/app.py` zobrazuje
-- viditelný příznak přímo v katalogu (uživatelův výslovný požadavek:
-- záznam zůstává vidět, ALE nese označení, že je ve frontě k revizi).
-- Detekce zapisuje i `data/incomplete_records_review_queue.json` (stejná
-- konvence jako ostatní `*_review_queue.json` v této pipeline).
ALTER TABLE Document
  ADD COLUMN needs_review BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN review_reason VARCHAR(500) NULL;

-- doc/PLAN.md §15 dodatek, 2026-09-15: "zdrojově agnostický" posun —
-- uživatel: operace nad databází nemají dál rozlišovat, ze které ze tří
-- původních tabulek (Prokop/Sinay/Haltuf) záznam vzešel; ty byly jen
-- "semínka" pro založení korpusu. `zdroj_dat` samo (JSON pole, nikdy
-- dřív nesahalo do DB) se PONECHÁVÁ jako čistě auditní/provenienční
-- sloupec (odkud tento záznam skutečně pochází), ALE nic v pipeline ani
-- v `app/app.py` už na něj nesmí větvit chování (viz `src/tools/
-- fetch_authoritative_metadata.py`/`fetch_fulltext.py` — přepnuty na
-- `typ_dokumentu`). `nazev_autoritativni`/`popis_autoritativni`/
-- `zdroj_autoritativni_url` (doc/PLAN.md §8/§9) a `jurisdikce_puvodni`
-- (§9) existovaly jen v JSON pipeline artefaktech a nikdy se nedostaly
-- do `Document` — po sloučení do `title`/`description`/`url`/
-- `jurisdikce` se ztratilo, zda šlo o ověřenou, nebo jen převzatou
-- hodnotu. Přidáno jako čistě doplňkové, nikdy nenahrazují resolvované
-- sloupce.
ALTER TABLE Document
  ADD COLUMN zdroj_dat VARCHAR(255) NULL,
  ADD COLUMN nazev_autoritativni VARCHAR(1000) NULL,
  ADD COLUMN popis_autoritativni TEXT NULL,
  ADD COLUMN zdroj_autoritativni_url VARCHAR(500) NULL,
  ADD COLUMN jurisdikce_puvodni VARCHAR(20) NULL;

-- doc/PLAN.md §15 dodatek, 2026-09-15: `Sinay_Zakony` dřív bal jeden
-- český zákon + jeho slovenský a unijní protějšek do JEDNOHO záznamu
-- (pole `nazev_eu`/`odkaz_eu`/`nazev_sk`/`odkaz_sk`) — na výslovné
-- přání uživatele se nyní štěpí na samostatné, provázané `Document`
-- záznamy (unijní verze je právně závazný originál, národní verze jsou
-- jeho odvozeniny). `IMPLEMENTS` (EU→národní) se znovupoužívá beze
-- změny — přesně vztah, který R1.3 už definuje. Pro pár CZ↔SK bez
-- unijního rodiče (žádný existující typ relace to nepokrývá) přidán
-- nový `NATIONAL_EQUIVALENT`.
ALTER TABLE document_relation
  MODIFY COLUMN relation_type
    ENUM('AMENDS','REPEALS','IMPLEMENTS','CONSOLIDATES','ADOPTS','NATIONAL_EQUIVALENT') NOT NULL;

-- doc/PLAN.md §17, 2026-09-16: anotace dogenerovaná, ne dohledaná.
-- Popis dohledaný u vydavatele (a přeložený do češtiny) patří do už
-- existujícího `popis_autoritativni` — to pole znamená "ověřeno u zdroje".
-- Pro záznamy, kde vydavatel žádný předmět/abstrakt nepublikuje, vzniká
-- shrnutí bez opory v cizím textu; to je jiná evidenční kategorie a NESMÍ
-- splynout s tou první. Proto vlastní sloupec: UI ho vykresluje s
-- označením "Přibližné shrnutí, neověřeno", `needs_review` zůstává
-- nastavené, a `Document.description` ho NIKDY nepřebírá (jinak by se
-- rozdíl ztratil a čtenář by nepoznal, co čte — přesně to, čemu se §13
-- rozhodlo předejít tím, že se vymyšlený popis raději nenapsal vůbec).
ALTER TABLE Document
  ADD COLUMN popis_priblizny TEXT NULL;

-- doc/PLAN.md §16, 2026-09-16: stabilní veřejný identifikátor záznamu.
-- `Document.id` je AUTO_INCREMENT přidělovaný pořadím vložení a
-- `src/tools/init_db.py` při každém běhu tabulku TRUNCATE-uje a nahrává
-- znovu — id se tedy při každém přesestavení přečíslují (§14 to zachytilo
-- živě: id 147, na které uživatel odkazoval, mezitím ukazovalo na úplně
-- jiný záznam). Dokud id sloužilo jen jako popisek v detailu (§12), bylo
-- to snesitelné; stránka konkrétního dokumentu ale existuje právě proto,
-- aby se na ni dalo odkazovat, takže potřebuje klíč odvozený z obsahu
-- záznamu. `slug` plní `src/tools/slug.py` (deterministicky, včetně
-- pořadí přidělování kolizních přípon) — viz jeho dokumentace.
ALTER TABLE Document
  ADD COLUMN slug VARCHAR(160) NULL UNIQUE;

-- ────────────────────────────────────────────────────────────
-- VRSTVA D (část) — číselníky, na které odkazuje vrstva B
-- ────────────────────────────────────────────────────────────

CREATE TABLE value_chain_stage (
  id    INT AUTO_INCREMENT PRIMARY KEY,
  code  VARCHAR(20)  NOT NULL UNIQUE,   -- VYROBA | DISTRIBUCE | SKLADOVANI | VYUZITI
  name  VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

-- ────────────────────────────────────────────────────────────
-- VRSTVA B — procesní vrstva (dle návrhu V02)
-- ────────────────────────────────────────────────────────────

CREATE TABLE process_class (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  code        VARCHAR(30)  NOT NULL UNIQUE,  -- UZEMNI | ENVIRONMENTALNI | STAVEBNI | ...
  name        VARCHAR(100) NOT NULL,
  description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE process_node (
  id               VARCHAR(3)   PRIMARY KEY,  -- U1 … U7
  name             VARCHAR(200) NOT NULL,
  chapter_ref      VARCHAR(10),
  process_class_id INT          NOT NULL,
  has_branches     BOOLEAN      NOT NULL DEFAULT FALSE,
  valid_from       DATE         NULL,
  valid_to         DATE         NULL,
  CONSTRAINT fk_pn_class FOREIGN KEY (process_class_id) REFERENCES process_class(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE node_description (
  node_id              VARCHAR(3) PRIMARY KEY,
  purpose              TEXT,
  role_in_phase        TEXT,
  trigger_condition    TEXT,
  key_decision_point   TEXT,
  v01_link_description TEXT,
  CONSTRAINT fk_nd_node FOREIGN KEY (node_id) REFERENCES process_node(id) ON DELETE CASCADE,
  FULLTEXT KEY ft_nd (purpose, trigger_condition, key_decision_point)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE node_branch (
  id                   INT AUTO_INCREMENT PRIMARY KEY,
  node_id              VARCHAR(3)   NOT NULL,
  branch_code          VARCHAR(5)   NOT NULL,   -- A | B | C | D | MAIN
  branch_name          VARCHAR(200),
  activation_condition TEXT,                    -- lidsky čitelný popis; strojová pravidla viz node_activation_rule
  description          TEXT,
  output_document      TEXT,
  is_default           BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_nb_node FOREIGN KEY (node_id) REFERENCES process_node(id) ON DELETE CASCADE,
  CONSTRAINT uq_nb UNIQUE (node_id, branch_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE branch_step (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  branch_id   INT          NOT NULL,
  step_number INT          NOT NULL,
  title       VARCHAR(300),
  description TEXT,
  CONSTRAINT fk_bs_branch FOREIGN KEY (branch_id) REFERENCES node_branch(id) ON DELETE CASCADE,
  CONSTRAINT uq_bs UNIQUE (branch_id, step_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE node_input (
  id                      INT AUTO_INCREMENT PRIMARY KEY,
  node_id                 VARCHAR(3) NOT NULL,
  seq_no                  INT,
  description             TEXT NOT NULL,
  is_specific_to_hydrogen BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_ni_node FOREIGN KEY (node_id) REFERENCES process_node(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE node_output (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  node_id             VARCHAR(3)   NOT NULL,
  branch_id           INT          NULL,      -- NULL = platí pro všechny větve
  document_name       VARCHAR(300) NOT NULL,
  description         TEXT,
  enables_next_node   VARCHAR(3)   NULL,
  is_project_blocking BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_no_node   FOREIGN KEY (node_id)           REFERENCES process_node(id) ON DELETE CASCADE,
  CONSTRAINT fk_no_branch FOREIGN KEY (branch_id)         REFERENCES node_branch(id),
  CONSTRAINT fk_no_next   FOREIGN KEY (enables_next_node) REFERENCES process_node(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE subject (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  name            VARCHAR(200) NOT NULL UNIQUE,
  abbreviation    VARCHAR(20),
  subject_type    VARCHAR(50),    -- orgán_veřejné_správy | provozovatel_sítě | investor | odborná_osoba | veřejnost
  competence_area VARCHAR(100),
  description     TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE node_subject (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  node_id               VARCHAR(3) NOT NULL,
  subject_id            INT        NOT NULL,
  process_role          TEXT,
  is_deciding_authority BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_ns_node    FOREIGN KEY (node_id)    REFERENCES process_node(id) ON DELETE CASCADE,
  CONSTRAINT fk_ns_subject FOREIGN KEY (subject_id) REFERENCES subject(id),
  CONSTRAINT uq_ns UNIQUE (node_id, subject_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE node_edge (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  from_node_id VARCHAR(3) NOT NULL,
  to_node_id   VARCHAR(3) NOT NULL,
  direction    VARCHAR(20) NOT NULL DEFAULT 'DIRECT'
               CHECK (direction IN ('DIRECT','REVERSE','BIDIRECTIONAL')),
  `character`  VARCHAR(30),   -- sekvenční | paralelní | zpětná | vzájemná | iterativní | nepřímá
  description  TEXT,
  CONSTRAINT fk_ne_from FOREIGN KEY (from_node_id) REFERENCES process_node(id) ON DELETE CASCADE,
  CONSTRAINT fk_ne_to   FOREIGN KEY (to_node_id)   REFERENCES process_node(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE installation_type (
  id                   INT AUTO_INCREMENT PRIMARY KEY,
  code                 VARCHAR(20)  NOT NULL UNIQUE,  -- ELEKTROLYZA | SKLADOVANI | VCS | VOZIDLA
  name                 VARCHAR(100),
  value_chain_stage_id INT NULL,                      -- FK místo textového value_chain_position
  description          TEXT,
  CONSTRAINT fk_it_vcs FOREIGN KEY (value_chain_stage_id) REFERENCES value_chain_stage(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE intensity_level (
  code          VARCHAR(20) PRIMARY KEY,   -- KLICOVY | VYZNAMNY | OKRAJOVY
  label         VARCHAR(50),               -- ●●● klíčový …
  numeric_level INT,
  description   TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE node_variability (
  id                   INT AUTO_INCREMENT PRIMARY KEY,
  node_id              VARCHAR(3)  NOT NULL,
  installation_type_id INT         NOT NULL,
  intensity_code       VARCHAR(20) NOT NULL,
  specifics            TEXT,
  CONSTRAINT fk_nv_node FOREIGN KEY (node_id)              REFERENCES process_node(id) ON DELETE CASCADE,
  CONSTRAINT fk_nv_it   FOREIGN KEY (installation_type_id) REFERENCES installation_type(id),
  CONSTRAINT fk_nv_il   FOREIGN KEY (intensity_code)       REFERENCES intensity_level(code),
  CONSTRAINT uq_nv UNIQUE (node_id, installation_type_id),
  FULLTEXT KEY ft_nv (specifics)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE node_problem (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  node_id       VARCHAR(3) NOT NULL,
  seq_no        INT,
  problem_title VARCHAR(300),
  description   TEXT,
  CONSTRAINT fk_np_node FOREIGN KEY (node_id) REFERENCES process_node(id) ON DELETE CASCADE,
  FULLTEXT KEY ft_np (description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE node_problem_installation (
  problem_id           INT NOT NULL,
  installation_type_id INT NOT NULL,
  PRIMARY KEY (problem_id, installation_type_id),
  CONSTRAINT fk_npi_problem FOREIGN KEY (problem_id)           REFERENCES node_problem(id) ON DELETE CASCADE,
  CONSTRAINT fk_npi_it      FOREIGN KEY (installation_type_id) REFERENCES installation_type(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

-- ────────────────────────────────────────────────────────────
-- VRSTVA C — integrační vazba uzel ↔ dokument
-- (nahrazuje legal_document, node_legal_document,
--  source_reference a node_source z návrhu V02)
-- ────────────────────────────────────────────────────────────

CREATE TABLE node_document (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  node_id          VARCHAR(3) NOT NULL,
  document_id      INT        NOT NULL,
  link_type        ENUM('LEGAL_BASIS','SOURCE') NOT NULL,
  is_primary_basis BOOLEAN NOT NULL DEFAULT FALSE,   -- smysluplné jen u LEGAL_BASIS
  relevance_note   TEXT,
  CONSTRAINT fk_ndoc_node FOREIGN KEY (node_id)     REFERENCES process_node(id) ON DELETE CASCADE,
  CONSTRAINT fk_ndoc_doc  FOREIGN KEY (document_id) REFERENCES Document(id)     ON DELETE RESTRICT,
  CONSTRAINT uq_ndoc UNIQUE (node_id, document_id, link_type),
  KEY ix_ndoc_doc (document_id)   -- směr „od předpisu k procesům"
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

-- ────────────────────────────────────────────────────────────
-- VRSTVA D — klasifikace a compliance (V03)
-- ────────────────────────────────────────────────────────────

CREATE TABLE technology_type (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  code        VARCHAR(40)  NOT NULL UNIQUE,  -- ELEKTROLYZER_PEM, TLAKOVY_ZASOBNIK, …
  name        VARCHAR(150) NOT NULL,
  description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE integration_level (
  id   INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(20)  NOT NULL UNIQUE,   -- SAMOSTATNA | INTEGROVANA | KOMPLEXNI | OSTROVNI
  name VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE application_area (
  id   INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(20)  NOT NULL UNIQUE,   -- MOBILITA | ENERGETIKA | PRUMYSL | PILOTNI
  name VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE project_criterion (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  code        VARCHAR(40)  NOT NULL UNIQUE,  -- KAPACITA_ELEKTROLYZERU, PRODEJ_TRETIM_STRANAM, …
  name        VARCHAR(150) NOT NULL,
  data_type   ENUM('NUMERIC','BOOLEAN','ENUM','TEXT') NOT NULL,
  unit        VARCHAR(20),
  description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE node_activation_rule (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  node_id           VARCHAR(3) NOT NULL,
  branch_id         INT        NULL,    -- NULL = aktivuje uzel jako celek
  criterion_id      INT        NOT NULL,
  comparator        ENUM('EQ','NE','GT','GTE','LT','LTE','IN','IS_TRUE','IS_FALSE') NOT NULL,
  value             VARCHAR(200) NULL,  -- u IN seznam oddělený ';'
  rule_group        INT NOT NULL DEFAULT 1,  -- AND uvnitř skupiny, OR mezi skupinami
  description       TEXT,               -- lidsky čitelné znění + výhrady k výkladové praxi
  basis_document_id INT NULL,           -- předpis stanovující práh/podmínku
  CONSTRAINT fk_nar_node   FOREIGN KEY (node_id)           REFERENCES process_node(id) ON DELETE CASCADE,
  CONSTRAINT fk_nar_branch FOREIGN KEY (branch_id)         REFERENCES node_branch(id),
  CONSTRAINT fk_nar_crit   FOREIGN KEY (criterion_id)      REFERENCES project_criterion(id),
  CONSTRAINT fk_nar_doc    FOREIGN KEY (basis_document_id) REFERENCES Document(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE use_case_scenario (
  id                   INT AUTO_INCREMENT PRIMARY KEY,
  code                 VARCHAR(40)  NOT NULL UNIQUE,  -- MALY_ELEKTROLYZER, HRS_VEREJNA, …
  name                 VARCHAR(200) NOT NULL,
  description          TEXT,
  application_area_id  INT NOT NULL,
  integration_level_id INT NOT NULL,
  CONSTRAINT fk_ucs_aa   FOREIGN KEY (application_area_id)  REFERENCES application_area(id),
  CONSTRAINT fk_ucs_intl FOREIGN KEY (integration_level_id) REFERENCES integration_level(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE scenario_value_chain (
  scenario_id INT NOT NULL,
  stage_id    INT NOT NULL,
  PRIMARY KEY (scenario_id, stage_id),
  CONSTRAINT fk_svc_scenario FOREIGN KEY (scenario_id) REFERENCES use_case_scenario(id) ON DELETE CASCADE,
  CONSTRAINT fk_svc_stage    FOREIGN KEY (stage_id)    REFERENCES value_chain_stage(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE scenario_technology (
  scenario_id        INT NOT NULL,
  technology_type_id INT NOT NULL,
  PRIMARY KEY (scenario_id, technology_type_id),
  CONSTRAINT fk_st_scenario FOREIGN KEY (scenario_id)        REFERENCES use_case_scenario(id) ON DELETE CASCADE,
  CONSTRAINT fk_st_tt       FOREIGN KEY (technology_type_id) REFERENCES technology_type(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE scenario_node (
  scenario_id    INT         NOT NULL,
  node_id        VARCHAR(3)  NOT NULL,
  intensity_code VARCHAR(20) NOT NULL,
  note           TEXT,
  PRIMARY KEY (scenario_id, node_id),
  CONSTRAINT fk_sn_scenario FOREIGN KEY (scenario_id)    REFERENCES use_case_scenario(id) ON DELETE CASCADE,
  CONSTRAINT fk_sn_node     FOREIGN KEY (node_id)        REFERENCES process_node(id),
  CONSTRAINT fk_sn_il       FOREIGN KEY (intensity_code) REFERENCES intensity_level(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE scenario_document (
  scenario_id    INT NOT NULL,
  document_id    INT NOT NULL,
  relevance_note TEXT,
  PRIMARY KEY (scenario_id, document_id),
  CONSTRAINT fk_sd_scenario FOREIGN KEY (scenario_id) REFERENCES use_case_scenario(id) ON DELETE CASCADE,
  CONSTRAINT fk_sd_doc      FOREIGN KEY (document_id) REFERENCES Document(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

-- ────────────────────────────────────────────────────────────
-- VRSTVA E — editorské účty, dvouosobní schvalovací proces oprav
-- `needs_review` položek a auditní log (doc/PLAN.md §42, 2026-09-18,
-- uživatelské zadání)
-- ────────────────────────────────────────────────────────────

-- Malá, ručně zakládaná skupina důvěryhodných editorů (žádná
-- samoregistrace, žádný reset hesla e-mailem — provisioning přes
-- `src/db/dbuser_add.py`/`src/db/dbuser_passwd.py`) — jediná role
-- `editor`, rozlišení "kdo smí co" řeší až `ReviewItem`'s vlastní
-- pravidlo níže (navrhovatel ≠ schvalovatel), ne sloupec role. `name`
-- (doc/PLAN.md §43, 2026-09-18, uživatelské zadání) je čitelné jméno
-- osoby — `username` je jen přihlašovací login, oboje se zadává zvlášť
-- při založení účtu. `email` (uživatelské zadání, 2026-09-18) — kontaktní
-- adresa, povinná a jedinečná stejně jako `username`, zadává se rovněž
-- při založení účtu (`dbuser_add.py`) a beze změny zůstává, dokud ji
-- nikdo ručně needituje přímo v databázi — žádný skript na její změnu
-- zatím není potřeba.
CREATE TABLE User (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  username       VARCHAR(100) NOT NULL UNIQUE,
  name           VARCHAR(200) NOT NULL,
  email          VARCHAR(255) NOT NULL UNIQUE,
  password_hash  VARCHAR(255) NOT NULL,
  is_active      TINYINT(1)   NOT NULL DEFAULT 1,
  created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

-- Jeden řádek = jeden cyklus návrh→rozhodnutí pro jeden `Document`.
-- Návrh (`proposed_changes_json`, {"pole": "nová hodnota", ...} — nikdy
-- jen jedno pole, aby šlo opravit víc věcí najednou) NEMĚNÍ `Document`
-- hned při vytvoření — teprve druhý, JINÝ editor rozhodne (potvrdí →
-- `apply_manual_corrections()`/live UPDATE, nebo zamítne). Zamítnutí
-- nemaže historii, zakládá nový cyklus (`needs_review` znovu), takže
-- celý sled pokusů zůstává viditelný v `AuditLog`. Vynuceno na dvou
-- úrovních zároveň (aplikace i CHECK) — druhý editor musí být SKUTEČNĚ
-- jiná osoba, ne jen jiné kliknutí téhož účtu.
CREATE TABLE ReviewItem (
  id                     INT AUTO_INCREMENT PRIMARY KEY,
  document_id            INT NOT NULL,
  review_reason          VARCHAR(500),
  status                 ENUM('needs_review','proposed','confirmed','rejected') NOT NULL DEFAULT 'needs_review',
  proposed_changes_json  TEXT,
  proposed_by_user_id    INT,
  proposed_at            TIMESTAMP NULL,
  confirmed_by_user_id   INT,
  confirmed_at           TIMESTAMP NULL,
  rejection_note         VARCHAR(500),
  created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ri_document  FOREIGN KEY (document_id)          REFERENCES Document(id) ON DELETE CASCADE,
  CONSTRAINT fk_ri_proposer  FOREIGN KEY (proposed_by_user_id)  REFERENCES User(id),
  CONSTRAINT fk_ri_confirmer FOREIGN KEY (confirmed_by_user_id) REFERENCES User(id),
  CONSTRAINT chk_ri_distinct_reviewers
    CHECK (confirmed_by_user_id IS NULL OR confirmed_by_user_id != proposed_by_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

-- Obecný auditní log (jedna tabulka pro všechny editovatelné entity, ne
-- jedna tabulka na entitu) — celý řádek před/po jako JSON, ne
-- sloupec-po-sloupci diff (jednoduší pro nízko-provozní interní nástroj,
-- kde přesnost na úrovni pole není potřeba). `review_item_id` (volitelné)
-- dohledá, KDO navrhl a KDO potvrdil/zamítl tu samou změnu —
-- `changed_by_user_id` sám o sobě nese jen toho, kdo provedl zápis
-- (schvalovatel), ne autora návrhu.
CREATE TABLE AuditLog (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  table_name          VARCHAR(100) NOT NULL,
  record_id           INT NOT NULL,
  action              VARCHAR(20)  NOT NULL,
  old_value_json      TEXT,
  new_value_json      TEXT,
  changed_by_user_id  INT NOT NULL,
  review_item_id      INT,
  changed_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_al_user        FOREIGN KEY (changed_by_user_id) REFERENCES User(id),
  CONSTRAINT fk_al_review_item FOREIGN KEY (review_item_id)     REFERENCES ReviewItem(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

-- ────────────────────────────────────────────────────────────
-- REFERENČNÍ DATA — číselníky
-- ────────────────────────────────────────────────────────────

INSERT INTO value_chain_stage (code, name) VALUES
  ('VYROBA',      'výroba vodíku'),
  ('DISTRIBUCE',  'distribuce a přeprava'),
  ('SKLADOVANI',  'skladování'),
  ('VYUZITI',     'využití');

INSERT INTO process_class (code, name, description) VALUES
  ('UZEMNI',          'územní',           'Územní plánování a rozhodování'),
  ('ENVIRONMENTALNI', 'environmentální',  'Posuzování vlivů na životní prostředí (EIA, IPPC), vodní režim'),
  ('STAVEBNI',        'stavební',         'Stavební řád, povolování staveb'),
  ('ENERGETICKY',     'energetický',      'Licencování a regulace energetických činností'),
  ('BEZPECNOSTNI',    'bezpečnostní',     'PZH/Seveso, požární ochrana, vyhrazená technická zařízení, ATEX'),
  ('INFRASTRUKTURNI', 'infrastrukturní',  'Připojení k elektrizační/plynárenské soustavě, vodovody, komunikace'),
  ('CERTIFIKACNI',    'certifikační',     'RFNBO, kvalita vodíku, záruky původu');

INSERT INTO intensity_level (code, label, numeric_level, description) VALUES
  ('KLICOVY',  '●●● klíčový',  3, 'Proces je pro danou oblast instalace klíčový'),
  ('VYZNAMNY', '●●○ významný', 2, 'Proces se uplatňuje významně'),
  ('OKRAJOVY', '●○○ okrajový', 1, 'Proces se uplatňuje okrajově nebo výjimečně');

INSERT INTO integration_level (code, name) VALUES
  ('SAMOSTATNA',  'samostatná instalace'),
  ('INTEGROVANA', 'integrovaný systém'),
  ('KOMPLEXNI',   'komplexní řešení (vodíkové údolí, průmyslový areál)'),
  ('OSTROVNI',    'ostrovní řešení');

INSERT INTO application_area (code, name) VALUES
  ('MOBILITA',   'vodíková mobilita'),
  ('ENERGETIKA', 'energetika'),
  ('PRUMYSL',    'průmyslové využití'),
  ('PILOTNI',    'výzkumné, pilotní a demonstrační projekty');

INSERT INTO installation_type (code, name, value_chain_stage_id, description) VALUES
  ('ELEKTROLYZA', 'výroba vodíku elektrolýzou',
     (SELECT id FROM value_chain_stage WHERE code='VYROBA'),
     'Elektrolyzéry a související výrobní infrastruktura'),
  ('SKLADOVANI',  'skladování a přeprava vodíku',
     (SELECT id FROM value_chain_stage WHERE code='SKLADOVANI'),
     'Zásobníky, sklady, přeprava ADR/RID'),
  ('VCS',         'vodíková čerpací stanice',
     (SELECT id FROM value_chain_stage WHERE code='DISTRIBUCE'),
     'Plnicí stanice včetně mobilních (HRS)'),
  ('VOZIDLA',     'vodíková vozidla',
     (SELECT id FROM value_chain_stage WHERE code='VYUZITI'),
     'Vozidla FCEV, registrace a technické kontroly');

INSERT INTO process_node (id, name, chapter_ref, process_class_id, has_branches) VALUES
  ('U1', 'Územní kompatibilita záměru',                 '6.2', (SELECT id FROM process_class WHERE code='UZEMNI'),          FALSE),
  ('U2', 'Environmentální režim projektu',              '6.3', (SELECT id FROM process_class WHERE code='ENVIRONMENTALNI'), TRUE),
  ('U3', 'Stavební povolení',                           '6.4', (SELECT id FROM process_class WHERE code='STAVEBNI'),        FALSE),
  ('U4', 'Energeticko-provozní oprávnění',              '6.5', (SELECT id FROM process_class WHERE code='ENERGETICKY'),     TRUE),
  ('U5', 'Bezpečnostní režim',                          '6.6', (SELECT id FROM process_class WHERE code='BEZPECNOSTNI'),    TRUE),
  ('U6', 'Připojení k infrastruktuře',                  '6.7', (SELECT id FROM process_class WHERE code='INFRASTRUKTURNI'), TRUE),
  ('U7', 'Příprava certifikační schopnosti dle RFNBO',  '6.8', (SELECT id FROM process_class WHERE code='CERTIFIKACNI'),    TRUE);
  -- Pozn.: název U7 dle V03; V02 uvádí „Certifikace produktu"

-- Procesní síť U1–U7 (dle V02-DB-popis §4.10)
INSERT INTO node_edge (from_node_id, to_node_id, direction, `character`) VALUES
  ('U1','U2','BIDIRECTIONAL','vzájemná'),
  ('U1','U3','DIRECT',       'sekvenční'),
  ('U1','U6','BIDIRECTIONAL','vzájemná'),
  ('U2','U3','DIRECT',       'sekvenční'),
  ('U2','U5','BIDIRECTIONAL','vzájemná'),
  ('U6','U2','DIRECT',       'nepřímá'),
  ('U2','U7','DIRECT',       'sekvenční'),
  ('U3','U5','BIDIRECTIONAL','vzájemná'),
  ('U6','U3','DIRECT',       'nepřímá'),
  ('U3','U4','DIRECT',       'sekvenční'),
  ('U4','U5','BIDIRECTIONAL','vzájemná'),
  -- doc/PLAN.md §34, 2026-09-17, uživatelské zadání (review process_layer_review_queue.json):
  -- povýšeno z DIRECT/'nepřímá' na BIDIRECTIONAL/'vzájemná' — typ licence (ERÚ)
  -- podmiňuje podmínky připojení K SOUSTAVĚ (U4→U6), ALE smlouvy o připojení
  -- jsou zase podmínkou licence ERÚ (U6→U4, s výjimkou ostrovního provozu) —
  -- oba směry jsou reálné, ne duplicitní popis téhož vztahu.
  ('U6','U4','BIDIRECTIONAL','vzájemná'),
  ('U4','U7','DIRECT',       'sekvenční'),
  ('U5','U6','DIRECT',       'sekvenční'),
  ('U6','U7','DIRECT',       'sekvenční'),
  -- doc/PLAN.md §34, 2026-09-17, uživatelské zadání (review process_layer_review_queue.json):
  -- bezpečnostní požadavky definované v U5 mohou vyloučit lokalitu nebo omezit
  -- kapacitu v U1 — zpětná vazba, ne sekvenční vztah; opačný směr (U1→U5) byl
  -- záměrně zamítnut jako duplicitní popis TÉHOŽ vztahu z druhé strany.
  ('U5','U1','DIRECT',       'zpětná'),
  -- funkční klasifikace v územním plánu (U1) může předurčit provozní/licenční
  -- režim dosažitelný v U4 — nový pár, dosud nezachycený v žádném směru.
  ('U1','U4','DIRECT',       'nepřímá'),
  -- provozní omezení z bezpečnostních důvodů (U5) mohou ovlivnit utilizaci
  -- elektrolyzéru a tím ekonomiku RFNBO certifikace (U7) — nový pár.
  ('U5','U7','DIRECT',       'nepřímá');

-- Matice variability 4×7 (intenzity dle V02-DB-popis §6; specifika doplnit z dokumentu V02)
INSERT INTO node_variability (node_id, installation_type_id, intensity_code)
SELECT v.node, it.id, v.intensity
FROM (
  SELECT 'U1' AS node, 'ELEKTROLYZA' AS itype, 'KLICOVY' AS intensity
  UNION ALL SELECT 'U1','SKLADOVANI','KLICOVY'  UNION ALL SELECT 'U1','VCS','KLICOVY'   UNION ALL SELECT 'U1','VOZIDLA','OKRAJOVY'
  UNION ALL SELECT 'U2','ELEKTROLYZA','KLICOVY' UNION ALL SELECT 'U2','SKLADOVANI','KLICOVY'
  UNION ALL SELECT 'U2','VCS','VYZNAMNY'        UNION ALL SELECT 'U2','VOZIDLA','OKRAJOVY'
  UNION ALL SELECT 'U3','ELEKTROLYZA','KLICOVY' UNION ALL SELECT 'U3','SKLADOVANI','KLICOVY'
  UNION ALL SELECT 'U3','VCS','KLICOVY'         UNION ALL SELECT 'U3','VOZIDLA','OKRAJOVY'
  UNION ALL SELECT 'U4','ELEKTROLYZA','KLICOVY' UNION ALL SELECT 'U4','SKLADOVANI','VYZNAMNY'
  UNION ALL SELECT 'U4','VCS','KLICOVY'         UNION ALL SELECT 'U4','VOZIDLA','OKRAJOVY'
  UNION ALL SELECT 'U5','ELEKTROLYZA','KLICOVY' UNION ALL SELECT 'U5','SKLADOVANI','KLICOVY'
  UNION ALL SELECT 'U5','VCS','KLICOVY'         UNION ALL SELECT 'U5','VOZIDLA','OKRAJOVY'
  UNION ALL SELECT 'U6','ELEKTROLYZA','KLICOVY' UNION ALL SELECT 'U6','SKLADOVANI','VYZNAMNY'
  UNION ALL SELECT 'U6','VCS','VYZNAMNY'        UNION ALL SELECT 'U6','VOZIDLA','OKRAJOVY'
  UNION ALL SELECT 'U7','ELEKTROLYZA','KLICOVY' UNION ALL SELECT 'U7','SKLADOVANI','OKRAJOVY'
  UNION ALL SELECT 'U7','VCS','VYZNAMNY'        UNION ALL SELECT 'U7','VOZIDLA','OKRAJOVY'
) v
JOIN installation_type it ON it.code = v.itype;

-- Další referenční data (větve, kroky, vstupy/výstupy, subjekty, problémy,
-- vazby node_document, aktivační pravidla, scénáře) se importují v rámci
-- migračních kroků 2–4 — viz Konsolidace-DB-popis.md §9.
