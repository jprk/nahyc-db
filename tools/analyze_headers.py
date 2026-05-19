import csv
import pathlib
import sys

# Force UTF-8 output for Windows console
sys.stdout.reconfigure(encoding='utf-8')

def extract_all_headers():
    temp_dir = pathlib.Path("Data")
    # Let's check the original non-processed files
    csv_files = [f for f in temp_dir.rglob("*.csv") if not f.name.endswith('_processed.csv')]
    
    unique_headers = set()
    file_headers = {}
    
    for csv_file in csv_files:
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f: # Use utf-8-sig to handle BOM
                reader = csv.reader(f, delimiter=';')
                headers = next(reader)
                # Clean up headers
                headers = [h.strip() for h in headers if h.strip()]
                unique_headers.update(headers)
                file_headers[str(csv_file)] = headers
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")
            
    print("All Unique Headers Custom across all files:")
    for header in sorted(unique_headers):
        print(f" - {header}")
        
    print("\nNon-standard headers found in files:")
    standard_cols = {'Typ dokumentu', 'Název dokumentu', 'Odpovědný resort', 'Jazyková verze', 'Platnost', 'Odkaz na zdroj', 'Poznámka'}
    for f, headers in file_headers.items():
        diff = set(headers) - standard_cols
        if diff:
            print(f" - {pathlib.Path(f).name}: {diff}")

if __name__ == "__main__":
    extract_all_headers()
