# Adresář doc/konsolidace

Adresář obsahuje Návrh konsolidovaného databázového schématu, které slučuje implementovanou databázi 
regulačních předpisů (výsledek DP004/V01) s procesní vrstvou uzlů U1–U7 (návrh z výsledku DP004/V02)
a doplňuje klasifikační a compliance vrstvu podle metodických požadavků výsledku DP004/V03.

| Soubor | Obsah                                                                                                                                                  |
|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Konsolidace-DB-popis.md` | Hlavní dokumentace: návrhová rozhodnutí, čtyřvrstvá architektura, popis tabulek, referenční compliance dotazy, migrační plán                           |
| `Konsolidace-DB-schema.puml` | UML (ER) schéma v PlantUML — vykreslit lze pomocí https://www.plantuml.com/plantuml                                                                    |
| `Konsolidace-DB-koncept.dot` | Konceptuální přehled vrstev (Graphviz DOT)                                                                                                             |
| `Konsolidace-DB-koncept.svg` / `.png` | Vyrenderovaný konceptuální diagram                                                                                                                     |
| `Konsolidace-DB-schema.sql` | SQL DDL skript pro MariaDB 11.x (aditivní migrace nad produkční V01) včetně referenčních dat číselníků, uzlů U1–U7, procesní sítě a matice variability |
| `Konsolidace-DB-pruvodce.docx` | Vysvětlující průvodce strukturou pro externí spolupracovníky — bez SQL, s diagramy, postupný výklad čtyř vrstev                                        |
| `obrazky/` | Zdrojové diagramy průvodce (Graphviz `.dot` + vyrenderovaná `.png`)                                                                                    |
