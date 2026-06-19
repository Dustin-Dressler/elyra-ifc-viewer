import os
import glob
import argparse
from ifc_processor import IfcProcessor

def main():
    print("--- Elyra IFC-Viewer Batch-Tool gestartet ---")
    
    # CLI-Setup
    parser = argparse.ArgumentParser(description="Automatische Generierung von 2D-Vektorplänen aus IFC-Modellen.")
    parser.add_argument("--input", default="data", help="Der Ordner, in dem die IFC-Dateien liegen (Standard: 'data').")
    parser.add_argument("--output", default="output", help="Der Zielordner für die SVG-Dateien (Standard: 'output').")
    args = parser.parse_args()

    data_dir = args.input
    output_dir = args.output
    
    # Prüft Input-Ordner
    if not os.path.exists(data_dir):
        print(f"Fehler: Der Eingabeordner '{data_dir}' existiert nicht.")
        return

    # Sucht alle .ifc Dateien
    ifc_files = glob.glob(os.path.join(data_dir, "*.ifc"))

    if not ifc_files:
        print(f"Fehler: Keine IFC-Dateien im Ordner '{data_dir}' gefunden.")
        return

    # Output-Ordner
    os.makedirs(output_dir, exist_ok=True)
    print(f"Gefundene IFC-Dateien: {len(ifc_files)} (Lade Vektor-Engine...)")

    for file_path in ifc_files:
        base_name = os.path.basename(file_path).replace(".ifc", "")
        print(f"\n{'='*50}")
        print(f"Verarbeite Gebäude: {base_name}")
        print(f"{'='*50}")

        
        processor = IfcProcessor(file_path)
        storeys = processor.get_storeys()

        # Generierung der Vektorgrafiken
        processor.generate_floor_plans(storeys, base_name=base_name, output_dir=output_dir)
        processor.generate_section(base_name=base_name, output_dir=output_dir)
        processor.generate_elevation(base_name=base_name, output_dir=output_dir)
    
    print(f"\nAlle Vektor-Pläne wurden erfolgreich im Ordner '{output_dir}/' gespeichert!")

if __name__ == "__main__":
    main()