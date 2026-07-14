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

# --- FUNCIÓN INTELIGENTE PARA EXTRAER Y CONVERTIR A CM ---
def extraer_y_convertir(texto):
    if not texto: return None
    
    # 1. Buscar 3 dimensiones en pulgadas (ej: 2.1 x 3.4 x 5 in)
    m3_in = re.search(r'([\d\.]+)\s*[xX*]\s*([\d\.]+)\s*[xX*]\s*([\d\.]+)\s*(?:in|inch|inches|”|")', texto, re.IGNORECASE)
    if m3_in:
        l, w, h = map(float, m3_in.groups())
        return f"{round(l*2.54, 1)} x {round(w*2.54, 1)} x {round(h*2.54, 1)} cm"
    
    # 2. Buscar 2 dimensiones en pulgadas
    m2_in = re.search(r'([\d\.]+)\s*[xX*]\s*([\d\.]+)\s*(?:in|inch|inches|”|")', texto, re.IGNORECASE)
    if m2_in:
        l, w = map(float, m2_in.groups())
        return f"{round(l*2.54, 1)} x {round(w*2.54, 1)} cm"

    # 3. Buscar 3 dimensiones en CM
    m3_cm = re.search(r'([\d\.]+)\s*[xX*]\s*([\d\.]+)\s*[xX*]\s*([\d\.]+)\s*(?:cm|centimeters|centímetros)', texto, re.IGNORECASE)
    if m3_cm:
        return f"{m3_cm.group(1)} x {m3_cm.group(2)} x {m3_cm.group(3)} cm"
        
    # 4. Buscar 2 dimensiones en CM
    m2_cm = re.search(r'([\d\.]+)\s*[xX*]\s*([\d\.]+)\s*(?:cm|centimeters|centímetros)', texto, re.IGNORECASE)
    if m2_cm:
        return f"{m2_cm.group(1)} x {m2_cm.group(2)} cm"

    # Si no detecta la fórmula matemática clara, lo ignoramos para evitar meter descripciones de relleno
    return None

print("Conectando al ERP para obtener catálogo...")
productos = {}
try:
    req = urllib.request.Request(PA_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        datos_erp = json.loads(response.read().decode('utf-8'))
        for item in datos_erp:
            cod = str(item.get("codigo", "")).strip().upper()
            desc = str(item.get("descripcion", "")).strip()
            if re.match(r'^(ANF|COF|REL|PUL)', cod) and desc:
                productos[cod] = desc
except Exception as e:
    print(f"Error descargando ERP: {e}")

nuevos = 0
for cod, desc in productos.items():
    if cod not in medidas and nuevos < 10:
        
        # Limpieza de título (Quitamos palabras genéricas para que Google encuentre la marca exacta)
        desc_limpia = re.sub(r'\(.*?\)', '', desc).strip()
        desc_limpia = re.sub(r'^(ANFORA|RELICARIO|COFRE|PULSERA|MINI)\s+', '', desc_limpia, flags=re.IGNORECASE).strip()
        
        print(f"[{nuevos+1}/10] Buscando: {cod} -> {desc_limpia[:40]}...")
        
        query = urllib.parse.quote(f'"{desc_limpia}" (dimensions OR size) (cm OR inches)')
        url = f"https://serpapi.com/search.json?q={query}&api_key={SERPAPI_KEY}"
        
        try:
            with urllib.request.urlopen(url, timeout=30) as res:
                data = json.loads(res.read().decode('utf-8'))
                
            snippet_valido = None
            
            # Primero intentamos sacar datos matemáticos de los resultados directos
            if "answer_box" in data and "snippet" in data["answer_box"]:
                snippet_valido = extraer_y_convertir(data["answer_box"]["snippet"])
            
            # Si no sirvió, escaneamos los primeros 3 resultados normales a ver si alguno tiene la medida técnica
            if not snippet_valido and "organic_results" in data:
                for result in data["organic_results"][:3]:
                    test_medida = extraer_y_convertir(result.get("snippet", ""))
                    if test_medida:
                        snippet_valido = test_medida
                        break
            
            # Guardamos el resultado (o indicamos que no hay datos técnicos públicos)
            if snippet_valido:
                medidas[cod] = snippet_valido
                print(f"   -> ¡Éxito! Medida limpia: {snippet_valido}")
            else:
                medidas[cod] = "No especificadas"
                print("   -> Sin datos técnicos. Guardado como No especificadas.")
            
            nuevos += 1
            time.sleep(2)
        except Exception as e:
            print(f"Error en {cod}: {e}")
            break

if nuevos > 0:
    with open(MEDIDAS_FILE, "w", encoding="utf-8") as f:
        json.dump(medidas, f, indent=4, ensure_ascii=False)
    print(f"Proceso finalizado. Total guardadas: {len(medidas)}")
else:
    print("No hay códigos nuevos por procesar.")
