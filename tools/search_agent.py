import os
import csv
import json
import logging
from duckduckgo_search import DDGS
from openai import OpenAI
import pathlib

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Read OpenAI API Key
API_KEY_PATH = ".openapi_key"
try:
    with open(API_KEY_PATH, 'r', encoding='utf-8') as f:
        api_key = f.read().strip()
    os.environ['OPENAI_API_KEY'] = api_key
    client = OpenAI()
except FileNotFoundError:
    logging.error(f"API key file not found at {API_KEY_PATH}")
    exit(1)

def web_search(query, max_results=3):
    logging.info(f"Searching for: {query}")
    try:
        results = DDGS().text(query, max_results=max_results)
        return "\n\n".join([f"Title: {r['title']}\nSnippet: {r['body']}\nURL: {r['href']}" for r in results])
    except Exception as e:
        logging.error(f"Search failed for query '{query}': {e}")
        return ""

def extract_info_no_search(document_title):
    """Uses OpenAI to extract the required fields based purely on its internal knowledge."""
    system_prompt = '''You are an expert legal data assistant for Czech and European regulatory documents. 
The user will provide the document title. Provide the following exact fields in JSON format:
{
    "Odpovědný resort": "The responsible ministry, organization, or EU body (e.g., MPO, MŽP, Evropská komise, Evropský parlament). Be concise.",
    "Jazyková verze": "The language (Usually 'čeština' or 'angličtina').",
    "Platnost": "The date the document entered into force or became valid (e.g., 1.1.2023).",
    "Odkaz na zdroj": "The official URL to the document (e.g., https://www.zakonyprolidi.cz/cs/YYYY-NNN or EUR-Lex link). Only output the URL.",
    "Poznámka": "Any brief, important note (max 1 sentence), or empty string."
}
Rely on your internal knowledge base. If you truly do not know a specific field, leave the string empty "". Do not invent invalid URLs.'''

    user_prompt = f"Document Title: {document_title}"
    
    try:
         completion = client.chat.completions.create(
             model="gpt-4o-mini",
             response_format={ "type": "json_object" },
             messages=[
                 {"role": "system", "content": system_prompt},
                 {"role": "user", "content": user_prompt}
             ],
             temperature=0.0
         )
         result = json.loads(completion.choices[0].message.content)
         return result
    except Exception as e:
         logging.error(f"LLM extraction failed for '{document_title}': {e}")
         return {}


def process_csv(filepath):
    logging.info(f"Processing file: {filepath}")
    output_rows = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        fieldnames = reader.fieldnames
        for row in reader:
            title = row.get('Název dokumentu', '').strip()
            
            # Skip empty rows or rows without title
            if not title:
                output_rows.append(row)
                continue
            
            # Check if all required fields are empty
            resort = row.get('Odpovědný resort', '').strip()
            link = row.get('Odkaz na zdroj', '').strip()
            
            if not resort or not link:
                logging.info(f"Querying LLM for: {title}")
                
                extracted_data = extract_info_no_search(title)
                logging.info(f"Extracted: {extracted_data}")
                
                # Update row only if the extracted value is not empty and the current value is empty
                for field in ['Odpovědný resort', 'Jazyková verze', 'Platnost', 'Odkaz na zdroj', 'Poznámka']:
                    if field in extracted_data and extracted_data[field] and not row.get(field, '').strip():
                        row[field] = extracted_data[field]
            
            output_rows.append(row)

    # Write back to file (we can overwrite or create a new file - let's write to a _processed version first during testing)
    output_filepath = filepath.replace('.csv', '_processed.csv')
    
    # Ensure standard fieldnames exist
    standard_fields = ['Typ dokumentu', 'Název dokumentu', 'Odpovědný resort', 'Jazyková verze', 'Platnost', 'Odkaz na zdroj', 'Poznámka']
    for sf in standard_fields:
        if sf not in fieldnames:
            fieldnames.append(sf)
            
    with open(output_filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(output_rows)
        
    logging.info(f"Saved processed data to {output_filepath}")


if __name__ == "__main__":
    temp_dir = pathlib.Path("Data")
    csv_files = list(temp_dir.rglob("*.csv"))
    
    # Filter out files that we already processed in previous runs
    csv_files = [f for f in csv_files if not f.name.endswith('_processed.csv')]
    
    logging.info(f"Found {len(csv_files)} CSV files to process in {temp_dir}.")
    
    for count, csv_file in enumerate(csv_files, 1):
        logging.info(f"--- Processing {count}/{len(csv_files)}: {csv_file} ---")
        process_csv(str(csv_file))
        
    logging.info("All files processed successfully!")
