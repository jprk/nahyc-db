# Normy — soupis technických norem k vodíku

| Soubor / adresář | Obsah |
|---|---|
| `sinay_normy_processed.json` | vstupní soupis 1 942 záznamů (zdroj Sinay); pole `Link` obsahuje jen obecné adresy normalizačních institucí |
| `resolve_normy_urls.py` | spouštěč nástroje, který ke každému záznamu dohledá jedinečnou adresu dokumentu |
| `url_resolver/` | vlastní nástroj (viz `url_resolver/README.md`) |
| `vystup/` | výsledky posledního běhu |

## Výsledek běhu z 11. 9. 2026

| Stav | Počet | Podíl |
|---|---:|---:|
| `OK` — jedinečná adresa ověřena | 1 550 | 79,8 % |
| `PŘIBLIŽNÉ` — nutná ruční kontrola | 15 | 0,8 % |
| `NELZE` — adresu nelze získat, uveden důvod | 377 | 19,4 % |

Podrobný rozpad podle vydavatelů i seznam všech nevyřešených záznamů
s odůvodněním je v `vystup/prehled-url.md`.

Soubor `vystup/http-cache.sqlite` je cache stažených odpovědí (~27 MB).
Není součástí výsledku, lze jej kdykoli smazat — jen se tím zpomalí další běh.
