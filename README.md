# IFC-Viewer CLI-Tool

Ein generisches Python-Tool zur automatisierten Extraktion von 2D-Planunterlagen (Grundrisse, vertikale Schnitte, Außenansichten) aus IFC-Gebäudemodellen.

## Features
* **Generische Batch-Verarbeitung:** Erkennt und verarbeitet automatisch alle `.ifc`-Dateien im `/data`-Ordner.
* **Geometrisch exakter vertikaler Schnitt:** Nutzt mathematisches Polygon-Clipping.
* **Professionelle Außenansicht:** Implementiert einen Painter’s Algorithm für undurchsichtige Fassadendarstellungen.

## Installation
Voraussetzung: Python 3.8+ installiert.

1. Repository klonen:
```bash
   git clone https://github.com/Dustin-Dressler/elyra-ifc-viewer.git
   cd elyra-ifc-project
```

2. Abhängigkeiten installieren:
```bash
   pip install -r requirements.txt
```

## Nutzung
Zu lesende .ifc Dateien müssen im `/data` Ordner liegen. Zum Starten des Tools diesen Befehl in das Terminal kopieren:
```bash
python main.py
```

Die generierte .svg Dateien landen dann im `/output` Ordner.