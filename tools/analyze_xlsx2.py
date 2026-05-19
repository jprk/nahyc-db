import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

excel_file = "2025-07-10_Databáze dokumentů H2.xlsx"
try:
    xls = pd.ExcelFile(excel_file)
    print("Sheets:", xls.sheet_names)
    
    for sheet_name in xls.sheet_names:
        print(f"\n=== Sheet: {sheet_name} ===")
        # Read the first 10 rows without headers to see the raw structure
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=10)
        df = df.dropna(axis=1, how='all')
        
        for idx, row in df.iterrows():
            row_vals = [str(x).replace('\n', ' ')[:50] for x in row.values]
            if any(val != 'nan' for val in row_vals):
                print(f"Row {idx}:", " | ".join(row_vals))
            
except Exception as e:
    print(f"Error: {e}")
