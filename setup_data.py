import os
import urllib.request

def download_sample_files():
    print("--- Starte Download der IFC-Beispieldateien ---")
    
    
    os.makedirs("data", exist_ok=True)
    
    # Drei Beispiel IFC-Datein
    ifc_files_to_download = {
        "AC20-FZK-Haus.ifc": "https://github.com/ibpsa/project1-wp-2-2-bim/raw/master/IFC_Files/MISC/AC20-FZK-Haus.ifc",
        "Duplex.ifc": "https://github.com/MadsHolten/BOT-Duplex-house/raw/refs/heads/master/Model%20files/IFC/Duplex.ifc",
        "Schependomlaan.ifc": "https://github.com/ibpsa/project1-wp-2-2-bim/raw/master/IFC_Files/MISC/Schependomlaan.ifc"
    }

    for filename, url in ifc_files_to_download.items():
        file_path = os.path.join("data", filename)
        
        
        if os.path.exists(file_path):
            print(f" -> '{filename}' existiert bereits. Wird übersprungen.")
            continue
            
        print(f" -> Lade '{filename}' von GitHub herunter (das kann je nach Internetverbindung kurz dauern)...")
        try:
            urllib.request.urlretrieve(url, file_path)
            print(f"    Erfolgreich gespeichert unter: {file_path}")
        except Exception as e:
            print(f"    Fehler beim Herunterladen von {filename}: {e}")

    print("\nSetup abgeschlossen! Deine Daten sind bereit.")

if __name__ == "__main__":
    download_sample_files()