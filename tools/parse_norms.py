import json
import pathlib
import sys

def parse_markdown_to_json(input_path, output_path):
    print(f"Reading from {input_path}")
    if not input_path.exists():
        print("Error: Input file does not exist.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    norms = []
    current_norm = None
    parsing_annotation = False
    
    # We can detect major sections using single hash "#"
    current_section = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect sections
        if line.startswith("# ") and not line.startswith("# **"):
            current_section = line[2:].strip()
            continue
            
        # A new norm entry often starts with a number followed by a dot, e.g. "1.  **"
        if line[0].isdigit() and line[1:].startswith(".  **") or line[1:].startswith(". **"):
            if current_norm:
                norms.append(current_norm)
                
            current_norm = {
                "Sekce": current_section,
                "Značka": line.split("**")[1].strip() if "**" in line else "",
                "Název": "",
                "Kategorie": "",
                "Platnost": "",
                "Anotace": "",
                "Klíčová slova": "",
                "Link": ""
            }
            parsing_annotation = False
            continue
            
        if not current_norm:
            continue
            
        if line.startswith("**Název:**"):
            current_norm["Název"] = line.replace("**Název:**", "").strip()
            parsing_annotation = False
        elif line.startswith("**Kategorie:**"):
            current_norm["Kategorie"] = line.replace("**Kategorie:**", "").strip()
            parsing_annotation = False
        elif line.startswith("**Platnost:**") or line.startswith("**Platnost**:"):
            current_norm["Platnost"] = line.replace("**Platnost:**", "").replace("**Platnost**:", "").strip()
            parsing_annotation = False
        elif line.startswith("**Anotace:**") or line.startswith("**Anotace**:"):
            current_norm["Anotace"] = line.replace("**Anotace:**", "").replace("**Anotace**:", "").strip()
            parsing_annotation = True # Annotation can span multiple lines
        elif line.startswith("**Klíčová slova:**") or line.startswith("**Klíčová slova**:"):
            current_norm["Klíčová slova"] = line.replace("**Klíčová slova:**", "").replace("**Klíčová slova**:", "").strip()
            parsing_annotation = False
        elif line.startswith("**Link:**") or line.startswith("**Link**:"):
            current_norm["Link"] = line.replace("**Link:**", "").replace("**Link**:", "").strip()
            parsing_annotation = False
        elif parsing_annotation:
            current_norm["Anotace"] += "\n" + line

    # Append the last fetched norm
    if current_norm:
         norms.append(current_norm)

    print(f"Extracted {len(norms)} norms.")
    
    # Write to JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(norms, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully saved to {output_path}")


if __name__ == "__main__":
    input_file = pathlib.Path("Data/20250303_Prokop/Normy vodik LD.md")
    output_file = pathlib.Path("Data/20250303_Prokop/normy_vodik.json")
    parse_markdown_to_json(input_file, output_file)
