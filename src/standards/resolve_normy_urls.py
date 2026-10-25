#!/usr/bin/env python3
"""Spouštěč nástroje pro doplnění jedinečných URL k normám.

Použití (z adresáře ``Normy``):

    python resolve_normy_urls.py
    python resolve_normy_urls.py --only STN --limit 50
    python resolve_normy_urls.py --explain "STN EN 17124/ - 2022.06"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from url_resolver.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
