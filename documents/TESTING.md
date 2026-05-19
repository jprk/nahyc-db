# Postup testování webové aplikace (Databáze H2)

Tento dokument popisuje přesný postup, jak lokálně spustit a otestovat webovou aplikaci pro vyhledávání regulačních předpisů.

## 1. Příprava a spuštění serveru

1. Otevřete příkazovou řádku (např. PowerShell) v kořenovém adresáři projektu.
2. Přejděte do složky aplikace:
   ```powershell
   cd app
   ```
3. Spusťte webový server pomocí Pythonu:
   ```powershell
   python app.py
   ```
   > [!NOTE]
   > Ujistěte se, že máte nainstalované požadované závislosti (především `Flask`). Server se standardně spustí v debug módu na portu 5000. Cesta k databázi je v `app.py` správně nastavena na `../db/regulatory_documents.db`.

## 2. Testování vyhledávání přes webový prohlížeč

1. Otevřete webový prohlížeč a přejděte na adresu: `http://127.0.0.1:5000/`.
2. Zobrazí se hlavní stránka "Katalog Regulačních Dokumentů H2" s vyhledávacím formulářem.
3. Pro otestování fulltextového vyhledávání zadejte do hlavního vyhledávacího pole (textového inputu) dotaz, například:
   - **`plyn`** - Aplikace by měla vrátit řadu nalezených dokumentů (např. evropské směrnice a nařízení týkající se trhu s plynem a vodíkem).
   - **`norma`** - V případě, že nejsou zrovna v databázi dokumenty obsahující přímo slovo "norma" v titulku nebo popisu, aplikace správně zahlásí "Žádné dokumenty nenalezeny".
4. Ověřte, že se při úspěšném hledání zobrazí u každého záznamu správné metainformace (Platnost od, Poznámka, atd.) a funkční odkaz na zdroj dokumentu (např. EUR-Lex).

## 3. Ukončení serveru

Až dokončíte testování, vraťte se do příkazové řádky, kde běží `app.py`, a stiskněte `CTRL+C` pro bezpečné ukončení lokálního webového serveru.
