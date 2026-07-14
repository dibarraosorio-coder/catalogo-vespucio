import os
import json
import csv
import urllib.request
import urllib.parse
import re
import time

# Configuración
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRvOH3xHFkBQ-BzvfRUi5rdXDT9pZOlgUXgvPFEpnyxphL5d282gGaEwm1_HggiW3iumBmhFTdEVQcr/pub?gid=1192465732&single=true&output=csv"
MEDIDAS_FILE = "medidas.json"

medidas = {}
if os.path.exists(MEDIDAS_FILE):
    with open(MEDIDAS_FILE, "r", encoding="utf-8") as f:
        try:
            medidas = json.load(f)
        except:
            medidas = {}

# 1. Descargar códigos
print("Descargando lista de productos...")
try:
    with urllib.request.urlopen(SHEET_URL, timeout=30) as response:
        lines = [l.decode('utf-8') for l in response.readlines()]
    codigos = []
    for line in lines:
        match = re.search(r'(ANF|COF|REL|PUL)\d+', line.upper())
        if match:
            codigos.append(match.group(0))
    codigos = list(set(codigos))
except Exception as e:
    print(f"Error descargando lista: {e}")
    codigos = []

# 2. Búsqueda por lotes (solo 10 por ejecución para asegurar que termine rápido)
nuevos = 0
for codigo in codigos:
    if codigo not in medidas and nuevos < 10:
        print(f"[{nuevos+1}/10] Buscando: {codigo}...")
        query = urllib.parse.quote(f'"{codigo}" urn OR relicario dimensions')
        url = f"https://serpapi.com/search.json?q={query}&api_key={SERPAPI_KEY}"
        
        try:
            with urllib.request.urlopen(url, timeout=30) as res:
                data = json.loads(res.read().decode('utf-8'))
                
            snippet = ""
            if "answer_box" in data and "snippet" in data["answer_box"]:
                snippet = data["answer_box"]["snippet"]
            elif "organic_results" in data and len(data["organic_results"]) > 0:
                snippet = data["organic_results"][0].get("snippet", "")
            
            if snippet:
                medidas[codigo] = snippet
                nuevos += 1
                time.sleep(2) # Pausa de 2 segundos para no saturar a Google/SerpApi
        except Exception as e:
            print(f"Error en {codigo}: {e}")
            break # Si algo falla, salimos del ciclo para guardar lo que llevamos

# 3. Guardar
if nuevos > 0:
    with open(MEDIDAS_FILE, "w", encoding="utf-8") as f:
        json.dump(medidas, f, indent=4, ensure_ascii=False)
    print(f"Proceso finalizado. Total de medidas en el catálogo: {len(medidas)}")
else:
    print("No se encontraron códigos nuevos por buscar.")
