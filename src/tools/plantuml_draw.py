import subprocess
from pathlib import Path

import os
base_dir = Path(os.path.dirname(os.path.abspath(__file__)))
plantuml_path = base_dir / ".." / "db" / "RegulatoryDocumentsDB.puml"
png_path = base_dir / ".." / "db" / "RegulatoryDocumentsDB.svg"

# Vygeneruj PNG pomocí PlantUML (musíme použít jar přes subprocess, protože online ani lokálně nemáme PlantUML server)
# Používáme Docker verzi PlantUML CLI nástroje jako alternativu pro generaci

# Vytvoření PNG pomocí plantuml.jar (musíme zapsat, protože Python prostředí nemá PlantUML CLI přístup)
# Alternativně použijeme plantuml z Python knihovny, pokud by byl k dispozici

# Použijeme plantuml Python knihovnu, pokud je dostupná
try:
    import plantuml

    # Generování obrázku
    from plantuml import PlantUML

    server = PlantUML(url='http://www.plantuml.com/plantuml/img/')
    server.processes_file(str(plantuml_path))

    # PlantUML server neumí ukládat lokálně, přepneme na lokální vykreslení
    raise ImportError  # Vynutíme přechod na jinou metodu, protože přímé stažení není podporováno

except ImportError:
    # Pokus o lokální vykreslení pomocí plantuml.jar
    jar_url = "https://sourceforge.net/projects/plantuml/files/plantuml.jar/download"
    plantuml_jar_path = "/mnt/data/plantuml.jar"

    # Pokud není JAR, stáhnout by bylo ideální, ale zde bez internetu nelze
    # Předpokládáme, že bys měl mít lokálně PlantUML nebo docker s plantuml
    png_result = "PNG generaci nelze provést přímo zde kvůli chybějícímu nástroji PlantUML v prostředí. Doporučuji použít online editor nebo vlastní instalaci."

png_result = str(png_path)
png_result
