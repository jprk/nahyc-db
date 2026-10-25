import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

excel_file = "2025-07-10_Databáze dokumentů H2.xlsx"
try:
    xls = pd.ExcelFile(excel_file)
    for sheet_name in xls.sheet_names:
        print(f"\n=== Sheet: {sheet_name} ===")
        df = pd.read_excel(xls, sheet_name=sheet_name, nrows=25)
        # Drop columns that are completely empty
        df = df.dropna(axis=1, how='all')
        
        # Print headers
        print(" | ".join([str(c) for c in df.columns]))
        print("-" * 40)
        
        # Print rows
        for _, row in df.iterrows():
            print(" | ".join([str(x).replace('\n', ' ')[:50] for x in row.values]))
            
except Exception as e:
    print(f"Error: {e}")
