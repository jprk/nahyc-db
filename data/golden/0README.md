# Adresář data/golden

Tematické golden sety — referenční seznamy předpisů, které databáze k danému tématu musí obsahovat
(nebo mít ve frontě kandidátů). Hlídají je testy v `tests/`.

* `rfnbo.json` — RFNBO (obnovitelná paliva nebiologického původu), podle auditu `doc/RFNBO_POKRYTI.md`;
  test `tests/test_golden_rfnbo.py` (priorita A chybí → test selže, priorita B → varování).
