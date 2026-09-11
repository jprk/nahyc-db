# DP004 V03 Database Requirements

**Project:** NAHYC DP004 — Vodíkový technologický inkubátor  
**Date:** 2026-09-11 15:37

This document outlines the requirements for the database system that will be developed for the DP004 project.


### R1.x Data Architecture & Management

1. **R1.1 - Record Uniqueness & Deduplication:** The system must enforce strict record uniqueness so that each distinct document is stored exactly once. The database schema must utilize primary keys and unique constraints (e.g., based on official document identification numbers) to physically prevent redundant entries.
2. **R1.2 - Jurisdictional Tiering:** The database schema must explicitly categorize every document into one of three distinct jurisdictional levels: international, European Union, or national.  
3. **R1.3 - Transposition & Dependency Mapping:** The system must support parent-child relational links between documents to explicitly track transpositions, specifically linking overarching EU directives to the specific national laws and executive regulations that implement them.  
4. **R1.4 - Standard Localization Linking:** The data model must manage the relationship between international technical standards and their localized equivalents (e.g., linking an ISO standard to its ČSN EN ISO counterpart) to prevent them from appearing as disconnected records.  
5. **R1.5 - Lifecycle & Version Control:** The versioning system must track more than just chronological iterations; it must explicitly capture the current validity state of each version (e.g., active, superseded, draft) while maintaining historical states and chronological change logs.  
6. **R1.6 - Authoritative Source Identification:** Every document must explicitly define its source of origin or authoritative institution (e.g., European Commission, national ministries, standard-setting bodies) via an independent classification table to allow filtering by jurisdiction and authority.  
7. **R1.7 - General Metadata Structure:** The database must continue to store comprehensive metadata for all documents, including IDs, titles, descriptions, and file paths.  
8. **R1.8 - Thematic Indexing:** The system must implement thematic indexing through a many-to-many relationship for keywords, allowing multiple tags (e.g., electrolyzer, distribution) to be assigned to a single document without data duplication.  
9. **R1.9 - Automated Maintenance:** The architecture must be capable of receiving automated or semi-automated updates reflecting legislative and regulatory changes.

### R2.x Search & Functional Capabilities

1. **R2.1 - Search Result Uniqueness:** The search logic must guarantee that each matching document is returned as a single reference in the output, preventing duplicate results even if a document matches multiple overlapping query parameters or keywords.  
2. **R2.2** The application must provide a responsive web-based user interface accessible via standard web browsers, requiring no specialized software installation.  
3. **R2.3** The main interface must feature a combined search engine that allows users to perform full-text queries while simultaneously applying structured filters for document type, responsible organ/source, and thematic keywords.  
4. **R2.4** Search results must display a summary of the document's metadata and, where permissible, provide direct hyperlinks to the original source files.  
5. **R2.5** The data structure must be modular and extensible, ensuring readiness for future data exports (e.g., in CSV, JSON, or XML formats) and the addition of new entities like specific projects or technological areas.

### R3.x Technical Stack

1. **R3.1** The application backend must be built using Python and the Flask web framework.  
2. **R3.2** The database layer must be a relational database, currently implemented as MariaDB, with initialization scripts to populate the data dynamically.  
3. **R3.3** The frontend must be constructed using HTML5, CSS3, and Jinja2 templates.  
4. **R3.4** The frontend design must utilize Vanilla JavaScript for basic interactivity without relying on massive JavaScript libraries, and incorporate Phosphor Icons and Google Fonts.

### R4.x Access Control & Licensing

1. **R4.1** The application must enforce licensing and visibility rules, ensuring that metadata is always publicly accessible while restricting direct access to the full text of documents that are protected by copyright or paid licenses (e.g., technical standards).  
2. **R4.2** The platform must serve as a central public hub for diverse stakeholders, including state administration, industrial manufacturers, transport operators, and research institutions.
