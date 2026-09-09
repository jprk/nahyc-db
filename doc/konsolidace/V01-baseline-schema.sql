-- ============================================================
-- NAHYC DP004 — V01 baseline schema (MariaDB 11.x)
-- Regulační dokumenty — základ, na který navazují ALTERy vrstvy A
-- v Konsolidace-DB-schema.sql.
--
-- Zdroj: db/RegulatoryDocumentsDB.puml (V01 UML, dohledán v historii
-- repozitáře) + sloupce/typy dle src/tools/init_db.py (SQLite varianta,
-- stejná data). Tabulky musí existovat PŘED aplikací Konsolidace-DB-schema.sql
-- — ta na ně provádí ALTER TABLE, nikoli CREATE TABLE.
-- ============================================================

CREATE TABLE DocumentType (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(255) NOT NULL UNIQUE,
  description TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE DocumentSource (
  id   INT AUTO_INCREMENT PRIMARY KEY,
  -- 768 chars, not 255: real data has combined "gestor" institution lists
  -- up to ~500 chars; this is near the max UNIQUE-index length MariaDB
  -- allows on a utf8mb4 VARCHAR (768 * 4 bytes = 3072-byte InnoDB cap).
  name VARCHAR(768) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE Keyword (
  id      INT AUTO_INCREMENT PRIMARY KEY,
  keyword VARCHAR(255) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE Document (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  -- 1000 chars, not 255: real titles are full EU regulation headers
  -- (observed max 461 chars in data/database_merged_deduplicated.json).
  title          VARCHAR(1000) NOT NULL,
  description    TEXT NULL,
  type_id        INT NULL,
  source_id      INT NULL,
  language       VARCHAR(50) NULL,
  url            VARCHAR(500) NULL,
  file_path      VARCHAR(255) NULL,
  -- 1000 chars, not 50: free-text validity notes, observed max 532 chars.
  effective_date VARCHAR(1000) NULL,
  version        INT NOT NULL DEFAULT 1,
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_document_type   FOREIGN KEY (type_id)   REFERENCES DocumentType(id),
  CONSTRAINT fk_document_source FOREIGN KEY (source_id) REFERENCES DocumentSource(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE DocumentVersion (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  document_id INT NOT NULL,
  version     INT NOT NULL,
  file_path   VARCHAR(255) NULL,
  change_log  TEXT NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_documentversion_document FOREIGN KEY (document_id) REFERENCES Document(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;

CREATE TABLE DocumentKeyword (
  document_id INT NOT NULL,
  keyword_id  INT NOT NULL,
  PRIMARY KEY (document_id, keyword_id),
  CONSTRAINT fk_documentkeyword_document FOREIGN KEY (document_id) REFERENCES Document(id),
  CONSTRAINT fk_documentkeyword_keyword  FOREIGN KEY (keyword_id)  REFERENCES Keyword(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci;
