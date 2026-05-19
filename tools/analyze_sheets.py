import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

excel_file = "2025-07-10_Databáze dokumentů H2.xlsx"
try:
    xls = pd.ExcelFile(excel_file)
    print("All sheets:", xls.sheet_names)
except Exception as e:
    print(f"Error: {e}")
