import fitz  # PyMuPDF
import json
import re

pdf_path = "../files/Knowledge_AI_Agent_Coach.pdf"
doc = fitz.open(pdf_path)

modules = []
current_module = None
current_text = []

for page_num, page in enumerate(doc):
    text = page.get_text()
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Detecta intestazione modulo (adatta il pattern se necessario)
        if re.match(r'^MODULO\s+\d+', line):
            if current_module:
                current_module['text'] = ' '.join(current_text).strip()
                modules.append(current_module)
            current_module = {'title': line, 'page': page_num+1}
            current_text = []
        else:
            if current_module:
                current_text.append(line)

if current_module:
    current_module['text'] = ' '.join(current_text).strip()
    modules.append(current_module)

print(f"Trovati {len(modules)} moduli")
with open('../output/modules_raw.json', 'w', encoding='utf-8') as f:
    json.dump(modules, f, ensure_ascii=False, indent=2)
print("Salvato in output/modules_raw.json")