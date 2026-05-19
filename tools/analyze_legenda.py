import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

excel_file = "2025-07-10_Databáze dokumentů H2.xlsx"
try:
    xls = pd.ExcelFile(excel_file)
    if 'Legenda' in xls.sheet_names:
        print("\n=== Sheet: Legenda ===")
        df = pd.read_excel(xls, sheet_name='Legenda', header=None, nrows=30)
        df = df.dropna(axis=1, how='all')
        for idx, row in df.iterrows():
            row_vals = [str(x).replace('\n', ' ')[:100] for x in row.values]
            if any(val != 'nan' for val in row_vals):
                print(f"Row {idx}:", " | ".join(row_vals))
except Exception as e:
    print(f"Error: {e}")
