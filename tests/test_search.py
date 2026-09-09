import unittest
import sys
import os
import re

# Přidání cesty, abychom mohli importovat app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.app import app

class SearchTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_energeticky_zakon_returns_one_record(self):
        # Odeslání dotazu
        response = self.app.get('/?q=Energetický+zákon')
        self.assertEqual(response.status_code, 200)
        
        html = response.data.decode('utf-8')
        
        # Očištění HTML od zbytečných mezer, abychom bezpečně našli titulek
        clean_html = re.sub(r'\s+', ' ', html)

        # Očekáváme, že se zákon 458/2000 Sb. zobrazí v HTML přesně jednou.
        # Původní chyba způsobovala, že se titulek vyrenderoval 3x. Hledáme
        # podle čísla zákona, ne podle přesného znění titulku — deduplikace
        # nyní tento záznam slučuje napříč zdroji (Sinay_Zakony +
        # Haltuf_Dokumenty) a vybírá nejúplnější dostupný název, takže
        # přesný text titulku se může v čase měnit (viz doc/PLAN.md Step 1).
        titles = re.findall(r'<div class="doc-title">([^<]*458/2000 Sb\.[^<]*)</div>', clean_html)

        self.assertEqual(len(titles), 1,
                          f"Očekával se právě jeden výskyt zákona 458/2000 Sb., ale bylo jich nalezeno {len(titles)}: {titles}")

if __name__ == '__main__':
    unittest.main()
