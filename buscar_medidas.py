import os
import json
import csv
import urllib.request
import urllib.parse
import re

# Configuración
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRvOH3xHFkBQ-BzvfRUi5rdXDT9pZOlgUXgvPFEpnyxphL5d282gGaEwm1_HggiW3iumBmhFTdEVQcr/pub?gid=1192465732&single=true&output=csv"
MEDIDAS_FILE = "medidas.json"

# 1. Cargar archivo local de medidas
medidas = {}
if os.path.exists(MEDIDAS_FILE):
    with open(MEDIDAS_FILE, "r", encoding="utf-8") as f:
        medidas = json.load(f)

# 2. Descargar códigos del Excel con TIMEOUT de 15 segundos
try:
    req = urllib.request.Request(SHEET_URL)
    with urllib.request.urlopen(req, timeout=15) as response:
        lines = [l.decode('utf-8') for l in response.readlines()]
        
    reader = csv.reader(lines)
    codigos = []
    for row in reader:
        for cell in row:
            if re.match(r'^(ANF|COF|REL|PUL)', cell.strip().upper()):
                codigos.append(cell.strip().upper())
                break
    codigos = list(set(codigos))
except Exception as e:
    print(f"Error al descargar el Excel: {e}")
    codigos = []

# 3. Buscar en Google vía SerpApi los códigos que falten
nuevos = 0
for codigo in codigos:
    if codigo not in medidas and nuevos < 80:
        print(f"Buscando medidas para: {codigo}")
        query = urllib.parse.quote(f'"{codigo}" urn OR relicario dimensions measurements')
        url = f"https://serpapi.com/search.json?q={query}&api_key={SERPAPI_KEY}"
        
        try:
            # Agregamos TIMEOUT de 15 segundos a la búsqueda
            with urllib.request.urlopen(url, timeout=15) as res:
                data = json.loads(res.read().decode('utf-8'))
                
            snippet = ""
            if "answer_box" in data and "snippet" in data["answer_box"]:
                snippet = data["answer_box"]["snippet"]
            elif "organic_results" in data and len(data["organic_results"]) > 0:
                snippet = data["organic_results"][0].get("snippet", "")
            
            if snippet:
                medidas[codigo] = snippet
                nuevos += 1
                
        except Exception as e:
            print(f"Error buscando {codigo}: {e}")

# 4. Guardar archivo actualizado
if nuevos > 0:
    with open(MEDIDAS_FILE, "w", encoding="utf-8") as f:
        json.dump(medidas, f, indent=4, ensure_ascii=False)
    print(f"Se actualizaron {nuevos} medidas nuevas.")
else:
    print("No hay códigos nuevos por buscar.")
