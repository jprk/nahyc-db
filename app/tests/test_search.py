import unittest
import sys
import os
import re

# Přidání cesty, abychom mohli importovat app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

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
        
        # Očekáváme, že se přesný titulek zobrazí v HTML přesně jednou.
        # Původní chyba způsobovala, že se titulek vyrenderoval 3x.
        target_title = '<div class="doc-title">Energetický zákon (č. 458/2000 Sb.)</div>'
        
        count = clean_html.count(target_title)
        self.assertEqual(count, 1, f"Očekával se právě jeden výskyt zákona, ale bylo jich nalezeno {count}.")

if __name__ == '__main__':
    unittest.main()
