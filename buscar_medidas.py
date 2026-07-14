import os
import json
import urllib.request
import urllib.parse
import re
import time

# Configuración
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
PA_URL = "https://defaultc9de65b0590045e8967debc553f353.81.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/a652c02764724cdc81b3868ca8ad5df0/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=I3jYEqWHJW0it2AsocfVtb-4pLtR--_brJvTdCzB-cA"
MEDIDAS_FILE = "medidas.json"

medidas = {}
if os.path.exists(MEDIDAS_FILE):
    with open(MEDIDAS_FILE, "r", encoding="utf-8") as f:
        try:
            medidas = json.load(f)
        except:
            medidas = {}

print("Conectando al ERP para obtener las descripciones de los productos...")
productos = {}
try:
    # Usamos tu conexión a Power Automate para leer las descripciones reales
    req = urllib.request.Request(PA_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        datos_erp = json.loads(response.read().decode('utf-8'))
        for item in datos_erp:
            cod = str(item.get("codigo", "")).strip().upper()
            desc = str(item.get("descripcion", "")).strip()
            if re.match(r'^(ANF|COF|REL|PUL)', cod) and desc:
                productos[cod] = desc
    print(f"Se cargaron {len(productos)} productos con descripción.")
except Exception as e:
    print(f"Error descargando catálogo ERP: {e}")


# 2. Búsqueda por lotes
nuevos = 0
for cod, desc in productos.items():
    if cod not in medidas and nuevos < 10:
        
        # Limpiamos textos como (DESCONTINUADO) o (MINI) para no confundir a Google
        desc_limpia = re.sub(r'\(.*?\)', '', desc).strip()
        
        print(f"[{nuevos+1}/10] Buscando: {cod} -> {desc_limpia[:40]}...")
        
        # ¡AQUÍ ESTÁ EL CAMBIO! Buscamos por la DESCRIPCIÓN en lugar del código
        query = urllib.parse.quote(f'"{desc_limpia}" dimensions OR measurements')
        url = f"https://serpapi.com/search.json?q={query}&api_key={SERPAPI_KEY}"
        
        try:
            with urllib.request.urlopen(url, timeout=30) as res:
                data = json.loads(res.read().decode('utf-8'))
                
            snippet = ""
            # Priorizar el cuadro de respuestas directas de Google
            if "answer_box" in data and "snippet" in data["answer_box"]:
                snippet = data["answer_box"]["snippet"]
            # Si no, tomar el fragmento del primer resultado
            elif "organic_results" in data and len(data["organic_results"]) > 0:
                snippet = data["organic_results"][0].get("snippet", "")
            
            if snippet:
                medidas[cod] = snippet
                nuevos += 1
                time.sleep(2) # Pausa por seguridad para que SerpApi no nos bloquee
        except Exception as e:
            print(f"Error en {cod}: {e}")
            break

# 3. Guardar resultados
if nuevos > 0:
    with open(MEDIDAS_FILE, "w", encoding="utf-8") as f:
        json.dump(medidas, f, indent=4, ensure_ascii=False)
    print(f"Proceso finalizado. Total de medidas guardadas en el catálogo: {len(medidas)}")
else:
    print("No se encontraron medidas nuevas en esta ejecución.")
