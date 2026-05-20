# Adresář /data/20250303_Prokop

Tento adresář obsahuje primárně zdrojová data a dokumenty zaměřené na oblast technických norem vodíkových technologií.

## Zpracování norem (Pipeline)
Z původního dodaného dokumentu `Normy vodik LD.docx` vzniká výsledný strojově čitelný soubor `normy_vodik.json` následujícím postupem:
1. **Extrakce textu:** K vytažení obsahu z DOCX do pracovního formátu Markdown (`Normy vodik LD.md`) lze využít skript `tools/read_docx.py`.
2. **Parsování struktury:** Následně se na tento pomocný `.md` soubor aplikuje skript `tools/parse_norms.py`, který strukturované textové bloky převede do podoby JSON záznamů (`normy_vodik.json`).

*(Poznámka: Pomocný soubor `Normy vodik LD.md` je verzovacím systémem Git ignorován).*
