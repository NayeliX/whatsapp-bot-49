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

# --- CONFIGURACIÓN ---
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")


# --- AUTENTICACIÓN GOOGLE SHEETS ---
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    print("✅ Conectado a Google Sheets exitosamente")
except Exception as e:
    print(f"❌ Error conectando a Google Sheets: {e}")
    sheet = None

# --- CONFIGURAR SERVIDOR FLASK ---
app = Flask(__name__)

def buscar_alumno_por_dni(dni: str) -> Optional[Dict]:
    """Busca un alumno en Google Sheets por su DNI/ID"""
    if not sheet:
        return None
    
    try:
        # Leer datos manualmente para manejar columnas duplicadas (múltiples "FECHA")
        # Obtener todos los valores del sheet
        valores = sheet.get_all_values()
        
        if not valores or len(valores) < 2:
            print("⚠️ El sheet está vacío o no tiene datos")
            return None
        
        # Primera fila son los encabezados
        headers = valores[0]
        # Filas siguientes son los datos
        filas_datos = valores[1:]
        
        dni_str = str(dni).strip()
        
        # Buscar la columna de ID/DNI (puede estar en diferentes posiciones)
        columna_id_index = None
        for i, header in enumerate(headers):
            header_upper = str(header).upper().strip()
            if header_upper == 'ID' or header_upper == 'DNI':
                columna_id_index = i
                break
        
        if columna_id_index is None:
            print("⚠️ No se encontró columna ID o DNI en el sheet")
            return None
        
        # Buscar el alumno por DNI
        alumno = None
        for fila in filas_datos:
            # Asegurar que la fila tenga suficientes columnas
            if len(fila) > columna_id_index:
                id_valor = str(fila[columna_id_index]).strip()
                if id_valor == dni_str:
                    # Construir diccionario con todos los valores de la fila
                    alumno = {}
                    for idx, header in enumerate(headers):
                        if idx < len(fila):
                            clave = str(header).strip()
                            valor = str(fila[idx]).strip()
                            
                            # Guardar siempre con índice para poder mapear correctamente
                            clave_con_indice = f"{clave}_{idx}"
                            alumno[clave_con_indice] = valor
                            
                            # También guardar sin índice la primera vez (para compatibilidad)
                            if clave not in alumno:
                                alumno[clave] = valor
                    break
        
        if alumno:
            print(f"✅ Alumno encontrado. Columnas disponibles: {list(alumno.keys())[:10]}...")  # Mostrar solo las primeras 10
        else:
            print(f"⚠️ No se encontró. DNI buscado: '{dni_str}'")
            # Debug: mostrar algunos IDs disponibles para ayudar
            if filas_datos:
                primeros_ids = []
                for fila in filas_datos[:3]:
                    if len(fila) > columna_id_index:
                        primeros_ids.append(str(fila[columna_id_index]).strip())
                print(f"   Primeros IDs en el Sheet: {primeros_ids}")
        
        return alumno
    except Exception as e:
        print(f"❌ Error buscando alumno: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return None

def obtener_mensaje_bienvenida() -> str:
    """Genera el mensaje de bienvenida del bot"""
    mensaje = "👋 *¡Bienvenido al Bot de Consulta de Estudiantes!*\n\n"
    mensaje += "📚 Este bot te permite consultar información de estudiantes usando su DNI.\n\n"
    mensaje += "💡 *¿Cómo usar el bot?*\n"
    mensaje += "Simplemente envía el DNI del estudiante que deseas consultar.\n\n"
    mensaje += "📝 *Ejemplo:*\n"
    mensaje += "Envía: `12345678`\n\n"
    mensaje += "El bot te responderá con:\n"
    mensaje += "• DNI del estudiante\n"
    mensaje += "• Nombre completo\n"
    mensaje += "• Notas disponibles\n\n"
    #mensaje += "🔍 *Comandos disponibles:*\n"
    #mensaje += "• `hola` - Muestra este mensaje de bienvenida\n"
    #mensaje += "• `inicio` - Muestra este mensaje de bienvenida\n"
    #mensaje += "• `[DNI]` - Consulta datos del estudiante\n\n"
    mensaje += "¡Empieza enviando un DNI! 🚀"
    return mensaje

def es_comando_bienvenida(texto: str) -> bool:
    """Verifica si el mensaje es un comando de bienvenida"""
    comandos = ['hola', 'hi', 'hello', 'inicio', 'start', 'menu', 'ayuda', 'help', 'comandos']
    texto_lower = texto.lower().strip()
    return texto_lower in comandos

def es_dni_valido(texto: str) -> bool:
    """Verifica si el texto parece ser un DNI (solo números)"""
    texto_limpio = texto.strip()
    # Un DNI debe tener al menos 6 dígitos y máximo 15, y solo contener números
    return texto_limpio.isdigit() and 6 <= len(texto_limpio) <= 15

def formatear_respuesta(alumno: Dict) -> str:
    """Formatea la respuesta con los datos del alumno"""
    respuesta = f"📄 *Datos del Estudiante*\n\n"
    
    # Obtener DNI/ID (intentar ambas opciones)
    dni = alumno.get('ID', alumno.get('DNI', 'N/A'))
    respuesta += f"🆔 *DNI:* {dni}\n"
    
    # Obtener nombre (intentar diferentes variantes)
    nombre = (alumno.get('Nombres y Apellidos') or 
              alumno.get('NOMBRES Y APELLIDOS') or 
              alumno.get('NOMBRES') or 
              alumno.get('Nombre') or 
              alumno.get('nombre') or
              'N/A')
    # Limpiar el nombre si está vacío
    if not nombre or str(nombre).strip() == '':
        nombre = 'N/A'
    respuesta += f"👤 *Nombre:* {nombre}\n"
    
    # Obtener el orden de las columnas del sheet para mantener el orden correcto
    columnas_ordenadas = []
    if sheet:
        try:
            # Obtener la primera fila (encabezados) para mantener el orden
            headers = sheet.row_values(1)
            columnas_ordenadas = [str(h).strip() if h else '' for h in headers]  # Convertir a string y limpiar
        except Exception as e:
            print(f"⚠️ Error obteniendo encabezados: {e}")
            # Si falla, usar las claves del diccionario (sin los índices)
            columnas_ordenadas = [k.split('_')[0] if '_' in k else k for k in alumno.keys()]
    else:
        # Si no hay sheet, usar las claves del diccionario
        columnas_ordenadas = [k.split('_')[0] if '_' in k else k for k in alumno.keys()]
    
    # Columnas a excluir (no son materias)
    columnas_excluidas = {'ID', 'DNI', 'Nombres y Apellidos', 'NOMBRES Y APELLIDOS', 
                          'NOMBRES', 'Nombre', 'nombre', ''}
    
    # Función auxiliar para verificar si una columna es una fecha (FECHA1, FECHA2, etc.)
    def es_columna_fecha(columna: str) -> bool:
        if not columna:
            return False
        columna_upper = columna.upper().strip()
        # Verificar si empieza con "FECHA" seguido de un número
        if columna_upper.startswith('FECHA'):
            # Verificar si después de "FECHA" hay un número
            resto = columna_upper[5:]  # Todo después de "FECHA"
            return resto.isdigit() if resto else False
        return False
    
    # Buscar materias y sus fechas correspondientes
    # Mostrar TODAS las materias, incluso si no tienen nota
    materias_con_notas = []
    
    i = 0
    while i < len(columnas_ordenadas):
        columna = columnas_ordenadas[i]
        columna_upper = columna.upper().strip() if columna else ''
        
        # Si la columna no está excluida y no es una columna de fecha, es una materia
        if columna and columna not in columnas_excluidas and not es_columna_fecha(columna):
            # Obtener la nota usando el índice de posición
            # Primero intentar con índice (formato: {columna}_{índice})
            clave_nota = f"{columna}_{i}"
            nota = alumno.get(clave_nota, '')
            
            # Si no se encuentra con índice, intentar sin índice (para compatibilidad)
            if not nota:
                nota = alumno.get(columna, '')
            
            nota_limpia = str(nota).strip() if nota else ''
            
            # Buscar la fecha correspondiente (siguiente columna que sea FECHA1, FECHA2, etc.)
            fecha_valor = ''
            if i + 1 < len(columnas_ordenadas):
                siguiente_columna = columnas_ordenadas[i + 1]
                if siguiente_columna and es_columna_fecha(siguiente_columna):
                    # Buscar el valor de la fecha usando el índice de posición (i+1)
                    clave_fecha = f"{siguiente_columna}_{i+1}"
                    fecha_valor = alumno.get(clave_fecha, '')
                    
                    # Si no se encuentra con índice, intentar sin índice
                    if not fecha_valor:
                        fecha_valor = alumno.get(siguiente_columna, '')
            
            # Formatear la fecha: mostrar el valor real si existe, si no mostrar mensaje
            fecha_limpia = str(fecha_valor).strip() if fecha_valor else ''
            if fecha_limpia and fecha_limpia.upper() != 'N/A':
                fecha_formato = fecha_limpia
            else:
                fecha_formato = "Fecha próxima a publicar"
            
            # Determinar qué mostrar como nota
            # Si tiene nota válida, mostrar la nota; si no, mostrar mensaje
            if nota_limpia and nota_limpia.upper() != 'N/A' and nota_limpia.upper() != '':
                nota_mostrar = nota_limpia
            else:
                nota_mostrar = "Aún no se asigna tu nota"
            
            # Agregar TODAS las materias, con o sin nota
            materias_con_notas.append((columna, nota_mostrar, fecha_formato))
        
        i += 1
    
    # Formatear las notas
    if materias_con_notas:
        respuesta += f"\n📊 *Notas:*\n\n"
        for materia, nota, fecha in materias_con_notas:
            respuesta += f"🧮{materia} ({fecha}): {nota}\n"
    else:
        respuesta += f"\n📊 *Notas:*\n"
        respuesta += "   No hay materias disponibles\n"
    
    return respuesta

def normalizar_numero(numero: str) -> str:
    """Normaliza el número de teléfono para WhatsApp API (sin +, solo dígitos)"""
    # Quitar espacios y el signo +
    numero = numero.replace(" ", "").replace("+", "").replace("-", "")
    # Asegurar que solo tenga dígitos
    return ''.join(filter(str.isdigit, numero))

def enviar_mensaje_whatsapp(numero: str, mensaje: str) -> bool:
    """Envía un mensaje por WhatsApp Business API"""
    try:
        # Normalizar el número
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
        
        print(f"📤 Intentando enviar mensaje a {numero_normalizado}...")
        print(f"   URL: {url}")
        print(f"   Payload: {payload}")
        
        response = requests.post(url, headers=headers, json=payload)
        
        # Log de la respuesta
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        
        # Validar respuesta
        if response.status_code == 200:
            response_data = response.json()
            print(f"✅ Mensaje enviado exitosamente")
            print(f"   Message ID: {response_data.get('messages', [{}])[0].get('id', 'N/A')}")
            return True
        else:
            print(f"❌ Error al enviar mensaje:")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            try:
                error_data = response.json()
                print(f"   Error details: {error_data}")
            except:
                pass
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión al enviar mensaje WhatsApp:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status Code: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado al enviar mensaje WhatsApp:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False

@app.route('/webhook', methods=['GET'])
def webhook_verify():
    """Verificación del webhook requerida por WhatsApp"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    # Debug: imprimir información recibida
    print(f"🔍 Verificación del webhook:")
    print(f"   Mode: {mode}")
    print(f"   Token recibido: {token}")
    print(f"   Token esperado: {WEBHOOK_VERIFY_TOKEN}")
    print(f"   Challenge: {challenge}")
    
    if mode == 'subscribe' and token == WEBHOOK_VERIFY_TOKEN:
        print("✅ Webhook verificado exitosamente")
        return challenge, 200
    else:
        print(f"❌ Error de verificación:")
        if mode != 'subscribe':
            print(f"   - Mode incorrecto: {mode} (esperado: 'subscribe')")
        if token != WEBHOOK_VERIFY_TOKEN:
            print(f"   - Token no coincide")
        return "Error de verificación", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    """Recibe y procesa mensajes de WhatsApp"""
    try:
        data = request.get_json()
        
        # Log completo del JSON recibido para debugging
        print("\n" + "="*60)
        print("📥 WEBHOOK RECIBIDO")
        print("="*60)
        print(f"📋 JSON completo recibido:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("="*60 + "\n")
        
        # Validar estructura básica
        if not data:
            print("⚠️ No se recibió ningún dato")
            return "ok", 200
        
        # Extraer información del mensaje
        if 'entry' not in data:
            print("⚠️ No se encontró 'entry' en el JSON")
            return "ok", 200
        
        if not data['entry']:
            print("⚠️ 'entry' está vacío")
            return "ok", 200
        
        entry = data['entry'][0]
        print(f"📦 Entry recibido: {entry.get('id', 'N/A')}")
        
        if 'changes' not in entry:
            print("⚠️ No se encontró 'changes' en entry")
            return "ok", 200
        
        if not entry['changes']:
            print("⚠️ 'changes' está vacío")
            return "ok", 200
        
        changes = entry['changes'][0]
        print(f"🔄 Change recibido: {changes.get('field', 'N/A')}")
        
        if 'value' not in changes:
            print("⚠️ No se encontró 'value' en changes")
            return "ok", 200
        
        value = changes['value']
        
        # Verificar si hay mensajes
        if 'messages' not in value:
            print("⚠️ No se encontró 'messages' en value (puede ser una notificación)")
            return "ok", 200
        
        messages = value['messages']
        if not messages:
            print("⚠️ 'messages' está vacío")
            return "ok", 200
        
        message_obj = messages[0]
        message_type = message_obj.get('type', 'unknown')
        print(f"📨 Tipo de mensaje: {message_type}")
        
        # Solo procesar mensajes de texto
        if message_type != 'text':
            print(f"⚠️ Mensaje ignorado (tipo: {message_type}, solo se procesan mensajes de texto)")
            return "ok", 200
        
        # Extraer texto y número
        message_text = message_obj.get('text', {}).get('body', '').strip()
        numero = message_obj.get('from', '')
        message_id = message_obj.get('id', 'N/A')
        
        print(f"\n📨 MENSAJE PROCESADO:")
        print(f"   ID: {message_id}")
        print(f"   De: {numero}")
        print(f"   Texto: {message_text}")
        
        if not message_text:
            print("⚠️ El mensaje está vacío")
            return "ok", 200
        
        if not numero:
            print("⚠️ No se pudo obtener el número del remitente")
            return "ok", 200
        
        # Verificar si es un comando de bienvenida
        if es_comando_bienvenida(message_text):
            print(f"👋 Comando de bienvenida detectado")
            respuesta = obtener_mensaje_bienvenida()
        # Verificar si parece ser un DNI válido
        elif es_dni_valido(message_text):
            # Buscar alumno por DNI
            print(f"🔍 Buscando DNI: {message_text}")
            alumno = buscar_alumno_por_dni(message_text)
            
            if alumno:
                print(f"✅ Alumno encontrado: {alumno.get('Nombres y Apellidos', 'N/A')}")
                respuesta = formatear_respuesta(alumno)
            else:
                print(f"⚠️ No se encontró alumno con DNI: {message_text}")
                # Mensaje de error con bienvenida
                respuesta = "⚠️ *No se encontró un estudiante con ese DNI.*\n\n"
                respuesta += "💡 *¿Qué puedes hacer?*\n"
                respuesta += "• Verifica que el DNI sea correcto\n"
                respuesta += "• Envía `hola` para ver las instrucciones\n"
                respuesta += "• Intenta con otro DNI\n\n"
                respuesta += "📝 *Ejemplo:* Envía `12345678`"
        else:
            # Mensaje no reconocido - mostrar bienvenida
            print(f"⚠️ Mensaje no reconocido: {message_text}")
            respuesta = "❓ *Mensaje no reconocido*\n\n"
            respuesta += obtener_mensaje_bienvenida()
        
        # Enviar respuesta
        print(f"\n📤 ENVIANDO RESPUESTA:")
        resultado = enviar_mensaje_whatsapp(numero, respuesta)
        
        if resultado:
            print(f"✅ Respuesta enviada exitosamente a {numero}")
        else:
            print(f"❌ Error al enviar respuesta a {numero}")
        
        print("="*60 + "\n")
        
    except KeyError as e:
        print(f"\n❌ ERROR: Clave faltante en estructura del mensaje")
        print(f"   Clave: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\n❌ ERROR PROCESANDO WEBHOOK:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        print(f"   Traceback: {traceback.format_exc()}")
        print("="*60 + "\n")
    
    return "ok", 200

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de salud para verificar que el servidor está funcionando"""
    return {
        "status": "ok",
        "google_sheets": "connected" if sheet else "disconnected"
    }, 200

if __name__ == '__main__':
    print("🚀 Iniciando servidor WhatsApp Bot...")
    print(f"📊 Google Sheet ID: {SPREADSHEET_ID}")
#    app.run(host='0.0.0.0', port=5000, debug=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


