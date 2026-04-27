from flask import Flask, request
import gspread
from google.oauth2.service_account import Credentials
import requests
import os
import json
import traceback
from dotenv import load_dotenv
load_dotenv()
from typing import Optional, Dict

# Define los alcances (scopes) requeridos por Google Sheets API
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# --- CONFIGURACIÓN ---
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")

# Define las hojas disponibles
HOJAS_DISPONIBLES = {
    "1": {
        "nombre": "Ciencia y Tecnología - Quinto de Secundaria",
        "hoja": "Calificaciones_Evaluaciones"
    },
    "2": {
        "nombre": "Academia Matemática NIVEL 1",
        "hoja": "academia_notas"
    }
}

# --- AUTENTICACIÓN GOOGLE SHEETS ---
credentials_info = os.getenv("GOOGLE_CREDENTIALS")
client = None
if credentials_info:
    try:
        creds_dict = json.loads(credentials_info)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        print("✅ Conectado a Google Sheets exitosamente")
    except Exception as e:
        print(f"❌ Error conectando a Google Sheets: {e}")
        traceback.print_exc()
        client = None
else:
    raise FileNotFoundError("❌ Variable GOOGLE_CREDENTIALS no encontrada en el entorno")

# --- CONFIGURAR SERVIDOR FLASK ---
app = Flask(__name__)

def obtener_mensaje_bienvenida() -> str:
    """Genera el mensaje de bienvenida del bot"""
    mensaje = "🙌 *Hola, bienvenido al asistente virtual académico del Prof Miguel Barrantes Flores 👨‍🔬*\n\n"
    mensaje += "Por favor, selecciona una opción:\n\n"
    mensaje += "1️⃣ *Ciencia y Tecnología - Quinto de Secundaria*\n"
    mensaje += "2️⃣ *Academia Matemática NIVEL 1*\n\n"
    mensaje += "Envía el número de la opción (1 o 2)"
    return mensaje

def obtener_mensaje_ingrese_dni(opcion: str) -> str:
    """Genera el mensaje pidiendo DNI para la opción seleccionada"""
    if opcion not in HOJAS_DISPONIBLES:
        return None
    
    nombre_hoja = HOJAS_DISPONIBLES[opcion]["nombre"]
    mensaje = f"✅ *{nombre_hoja}* seleccionada\n\n"
    mensaje += "Por favor, ingresa tu número de DNI:\n\n"
    mensaje += "📝 *Ejemplo:* `12345678`\n\n"
    mensaje += "─" * 30 + "\n"
    mensaje += "3️⃣ *Volver al menú principal*"
    return mensaje

def es_opcion_valida(texto: str) -> bool:
    """Verifica si el texto es una opción válida (1 o 2)"""
    texto_limpio = texto.strip()
    return texto_limpio in HOJAS_DISPONIBLES.keys()

def es_opcion_volver_menu(texto: str) -> bool:
    """Verifica si el usuario quiere volver al menú (opción 3)"""
    texto_limpio = texto.strip()
    return texto_limpio == "3"

def es_dni_valido(texto: str) -> bool:
    """Verifica si el texto parece ser un DNI (solo números)"""
    texto_limpio = texto.strip()
    return texto_limpio.isdigit() and 6 <= len(texto_limpio) <= 15

def buscar_alumno_por_dni(dni: str, numero_hoja: str) -> Optional[Dict]:
    """Busca un alumno en Google Sheets por su DNI/ID en la hoja especificada"""
    if not client:
        print("❌ Cliente de Google Sheets no inicializado")
        return None
    
    try:
        nombre_hoja = HOJAS_DISPONIBLES[numero_hoja]["hoja"]
        print(f"📋 Buscando en hoja: {nombre_hoja}")
        
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        hoja = spreadsheet.worksheet(nombre_hoja)
        
        valores = hoja.get_all_values()
        
        if not valores or len(valores) < 2:
            print("⚠️ La hoja está vacía o no tiene datos")
            return None
        
        headers = valores[0]
        filas_datos = valores[1:]
        
        dni_str = str(dni).strip()
        
        columna_id_index = None
        for i, header in enumerate(headers):
            header_upper = str(header).upper().strip()
            if header_upper == 'ID' or header_upper == 'DNI':
                columna_id_index = i
                print(f"   ✅ Columna DNI/ID encontrada en índice {i}: '{header}'")
                break
        
        if columna_id_index is None:
            print("⚠️ No se encontró columna ID o DNI en la hoja")
            print(f"   Encabezados disponibles: {headers}")
            return None
        
        alumno = None
        for fila in filas_datos:
            if len(fila) > columna_id_index:
                id_valor = str(fila[columna_id_index]).strip()
                if id_valor == dni_str:
                    alumno = {}
                    for idx, header in enumerate(headers):
                        if idx < len(fila):
                            clave = str(header).strip()
                            valor = str(fila[idx]).strip()
                            
                            clave_con_indice = f"{clave}_{idx}"
                            alumno[clave_con_indice] = valor
                            
                            if clave not in alumno:
                                alumno[clave] = valor
                    break
        
        if alumno:
            print(f"✅ Alumno encontrado en {nombre_hoja}")
        else:
            print(f"⚠️ No se encontró alumno con DNI: '{dni_str}' en {nombre_hoja}")
        
        return alumno
    except Exception as e:
        print(f"❌ Error buscando alumno en hoja {numero_hoja}: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return None

def formatear_respuesta(alumno: Dict, numero_hoja: str) -> str:
    """Formatea la respuesta con los datos del alumno"""
    respuesta = f"📄 *Datos del Estudiante*\n\n"
    
    dni = alumno.get('ID', alumno.get('DNI', 'N/A'))
    respuesta += f"🆔 *DNI:* {dni}\n"
    
    nombre = (alumno.get('Nombres y Apellidos') or 
              alumno.get('NOMBRES Y APELLIDOS') or 
              alumno.get('NOMBRES') or 
              alumno.get('Nombre') or 
              alumno.get('nombre') or
              'N/A')
    if not nombre or str(nombre).strip() == '':
        nombre = 'N/A'
    respuesta += f"👤 *Nombre:* {nombre}\n"
    
    columnas_ordenadas = []
    try:
        nombre_hoja = HOJAS_DISPONIBLES[numero_hoja]["hoja"]
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        hoja = spreadsheet.worksheet(nombre_hoja)
        headers = hoja.row_values(1)
        columnas_ordenadas = [str(h).strip() if h else '' for h in headers]
    except Exception as e:
        print(f"⚠️ Error obteniendo encabezados: {e}")
        columnas_ordenadas = [k.split('_')[0] if '_' in k else k for k in alumno.keys()]
    
    columnas_excluidas = {'ID', 'DNI', 'Nombres y Apellidos', 'NOMBRES Y APELLIDOS', 
                          'NOMBRES', 'Nombre', 'nombre', ''}
    
    def es_columna_fecha(columna: str) -> bool:
        if not columna:
            return False
        columna_upper = columna.upper().strip()
        if columna_upper.startswith('FECHA'):
            resto = columna_upper[5:]
            return resto.isdigit() if resto else False
        return False
    
    materias_con_notas = []
    
    i = 0
    while i < len(columnas_ordenadas):
        columna = columnas_ordenadas[i]
        columna_upper = columna.upper().strip() if columna else ''
        
        if columna and columna not in columnas_excluidas and not es_columna_fecha(columna):
            clave_nota = f"{columna}_{i}"
            nota = alumno.get(clave_nota, '')
            
            if not nota:
                nota = alumno.get(columna, '')
            
            nota_limpia = str(nota).strip() if nota else ''
            
            fecha_valor = ''
            if i + 1 < len(columnas_ordenadas):
                siguiente_columna = columnas_ordenadas[i + 1]
                if siguiente_columna and es_columna_fecha(siguiente_columna):
                    clave_fecha = f"{siguiente_columna}_{i+1}"
                    fecha_valor = alumno.get(clave_fecha, '')
                    
                    if not fecha_valor:
                        fecha_valor = alumno.get(siguiente_columna, '')
            
            fecha_limpia = str(fecha_valor).strip() if fecha_valor else ''
            fecha_formato = fecha_limpia if (fecha_limpia and fecha_limpia.upper() != 'N/A') else "-"
            
            nota_mostrar = nota_limpia if (nota_limpia and nota_limpia.upper() != 'N/A' and nota_limpia.upper() != '') else "-"
            
            materias_con_notas.append((columna, nota_mostrar, fecha_formato))
        
        i += 1
    
    if materias_con_notas:
        respuesta += f"\n📊 *Notas:*\n\n"
        for materia, nota, fecha in materias_con_notas:
            respuesta += f"🧮 {materia} / {fecha} / {nota}\n"
    else:
        respuesta += f"\n📊 *Notas:*\n"
        respuesta += "   No hay materias disponibles\n"
    
    return respuesta

def normalizar_numero(numero: str) -> str:
    """Normaliza el número de teléfono para WhatsApp API"""
    numero = numero.replace(" ", "").replace("+", "").replace("-", "")
    return ''.join(filter(str.isdigit, numero))

def enviar_mensaje_whatsapp(numero: str, mensaje: str) -> bool:
    """Envía un mensaje por WhatsApp Business API"""
    try:
        numero_normalizado = normalizar_numero(numero)
        
        url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": numero_normalizado,
            "type": "text",
            "text": {"body": mensaje}
        }
        
        print(f"📤 Enviando mensaje a {numero_normalizado}...")
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            print(f"✅ Mensaje enviado exitosamente")
            return True
        else:
            print(f"❌ Error al enviar mensaje: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}")
        return False

@app.route('/webhook', methods=['GET'])
def webhook_verify():
    """Verificación del webhook requerida por WhatsApp"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    print(f"🔍 Verificación del webhook: mode={mode}, token={token}")
    
    if mode == 'subscribe' and token == WEBHOOK_VERIFY_TOKEN:
        print("✅ Webhook verificado exitosamente")
        return challenge, 200
    else:
        print(f"❌ Error de verificación")
        return "Error de verificación", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    """Recibe y procesa mensajes de WhatsApp"""
    try:
        data = request.get_json()
        
        print("\n" + "="*60)
        print("📥 WEBHOOK RECIBIDO")
        print("="*60)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("="*60 + "\n")
        
        if not data or 'entry' not in data or not data['entry']:
            return "ok", 200
        
        entry = data['entry'][0]
        
        if 'changes' not in entry or not entry['changes']:
            return "ok", 200
        
        changes = entry['changes'][0]
        
        if 'value' not in changes:
            return "ok", 200
        
        value = changes['value']
        
        if 'messages' not in value or not value['messages']:
            return "ok", 200
        
        message_obj = value['messages'][0]
        message_type = message_obj.get('type', 'unknown')
        
        if message_type != 'text':
            return "ok", 200
        
        message_text = message_obj.get('text', {}).get('body', '').strip()
        numero = message_obj.get('from', '')
        
        print(f"📨 Mensaje de {numero}: {message_text}")
        
        if not message_text or not numero:
            return "ok", 200
        
        # Máquina de estados
        if not hasattr(webhook, 'user_states'):
            webhook.user_states = {}
        
        user_state = webhook.user_states.get(numero, {})
        estado_actual = user_state.get('estado', 'seleccionar_hoja')
        opcion_seleccionada = user_state.get('opcion', None)
        
        print(f"Estado: {estado_actual}, Opción: {opcion_seleccionada}")
        
        # VERIFICAR SI USUARIO QUIERE VOLVER AL MENÚ (opción 3)
        if es_opcion_volver_menu(message_text):
            print(f"🔄 Usuario presionó volver al menú")
            webhook.user_states[numero] = {'estado': 'seleccionar_hoja'}
            respuesta = obtener_mensaje_bienvenida()
        
        # PERMITIR CAMBIO DE OPCIÓN EN CUALQUIER MOMENTO (1 o 2)
        elif es_opcion_valida(message_text):
            print(f"✅ Usuario cambió a opción: {message_text}")
            opcion = message_text.strip()
            webhook.user_states[numero] = {
                'estado': 'ingresar_dni',
                'opcion': opcion
            }
            respuesta = obtener_mensaje_ingrese_dni(opcion)
        
        elif estado_actual == 'seleccionar_hoja':
            # Usuario escribió algo que no es 1 o 2, simplemente mostrar bienvenida
            print(f"⚠️ Mensaje inicial ignorado: {message_text}")
            respuesta = obtener_mensaje_bienvenida()
        
        elif estado_actual == 'ingresar_dni':
            if es_dni_valido(message_text):
                alumno = buscar_alumno_por_dni(message_text, opcion_seleccionada)
                
                if alumno:
                    respuesta = formatear_respuesta(alumno, opcion_seleccionada)
                    webhook.user_states[numero] = {'estado': 'seleccionar_hoja'}
                    respuesta += "\n\n" + "─" * 30
                    respuesta += "\n¿Deseas consultar otro DNI?\n"
                    respuesta += obtener_mensaje_bienvenida()
                else:
                    respuesta = "⚠️ *No se encontró estudiante con ese DNI.*\n\n"
                    respuesta += "💡 Verifica que el DNI sea correcto e intenta de nuevo.\n\n"
                    respuesta += "📝 *Ejemplo:* `12345678`"
            else:
                respuesta = "❌ *DNI no válido*\n\n"
                respuesta += "El DNI debe contener entre 6 y 15 dígitos.\n\n"
                respuesta += obtener_mensaje_ingrese_dni(opcion_seleccionada)
        
        else:
            webhook.user_states[numero] = {'estado': 'seleccionar_hoja'}
            respuesta = obtener_mensaje_bienvenida()
        
        print(f"\n📤 Enviando respuesta...")
        resultado = enviar_mensaje_whatsapp(numero, respuesta)
        
        if resultado:
            print(f"✅ Respuesta enviada a {numero}")
        
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"❌ Error en webhook: {e}")
        print(traceback.format_exc())
    
    return "ok", 200

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de salud"""
    return {
        "status": "ok",
        "google_sheets": "connected" if client else "disconnected"
    }, 200

@app.route('/')
def home():
    return "✅ Bot de WhatsApp activo"
    
if __name__ == '__main__':
    print("🚀 Iniciando servidor WhatsApp Bot...")
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)