# WhatsApp Bot - Consulta de Estudiantes por DNI

Bot de WhatsApp Business que permite consultar información de estudiantes desde Google Sheets usando su DNI como identificador.

## 🚀 Características

- ✅ Consulta de estudiantes por DNI
- ✅ Integración con WhatsApp Business API
- ✅ Conexión a Google Sheets
- ✅ Respuesta automática con datos del estudiante (Nombre, Notas, etc.)
- ✅ Detección automática de columnas de notas (NOTA1, NOTA2, etc.)

## 📋 Requisitos Previos

1. **Cuenta de WhatsApp Business API** (Meta for Developers)
2. **Cuenta de Google** para acceder a Google Sheets
3. **Python 3.8 o superior**

## 🔧 Instalación

### 1. Clonar o descargar el proyecto

```bash
cd whatsApp-Bot-49
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar Google Sheets

#### Paso 1: Crear una cuenta de servicio en Google Cloud

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la **Google Sheets API**
4. Ve a **IAM & Admin** > **Service Accounts**
5. Crea una nueva cuenta de servicio
6. Descarga el archivo JSON de credenciales
7. Renombra el archivo a `credentials.json` y colócalo en la carpeta del proyecto

#### Paso 2: Compartir tu Google Sheet

1. Abre tu Google Sheet
2. Haz clic en **Compartir** (Share)
3. Agrega el email de la cuenta de servicio (está en el archivo `credentials.json`, campo `client_email`)
4. Dale permisos de **Editor** o **Visualizador** (solo lectura es suficiente)

#### Paso 3: Obtener el ID de tu Google Sheet

El ID está en la URL de tu hoja de cálculo:
```
https://docs.google.com/spreadsheets/d/ID_AQUI/edit#gid=0
```

Copia el `ID_AQUI` y úsalo en la configuración.

#### Paso 4: Estructura de tu Google Sheet

Tu hoja debe tener al menos estas columnas:
- **DNI** (primera columna con el DNI del estudiante)
- **NOMBRES** (nombre del estudiante)
- **NOTA1**, **NOTA2**, etc. (columnas con las notas)

Ejemplo:
| DNI | NOMBRES | NOTA1 | NOTA2 | NOTA3 |
|-----|---------|-------|-------|-------|
| 12345678 | Juan Pérez | 85 | 90 | 88 |

### 4. Configurar WhatsApp Business API

#### Paso 1: Obtener el Access Token

1. Ve a [Meta for Developers](https://developers.facebook.com/)
2. Crea una app o selecciona una existente
3. Agrega el producto **WhatsApp**
4. Obtén tu **Access Token** desde la configuración de WhatsApp

#### Paso 2: Obtener el Phone Number ID

1. En la configuración de WhatsApp, encontrarás tu **Phone Number ID**
2. Este ID se necesita para enviar mensajes

#### Paso 3: Configurar el Webhook

1. Configura la URL de tu webhook: `https://tu-dominio.com/webhook`
2. Para desarrollo local, puedes usar **ngrok**:
   ```bash
   ngrok http 5000
   ```
3. Usa la URL de ngrok como webhook en Meta for Developers
4. El token de verificación es: `mi_token_secreto_123` (o el que configures)

## ⚙️ Configuración

Tienes dos opciones para configurar:

### Opción 1: Variables de entorno (Recomendado)

Crea un archivo `.env` o configura las variables de entorno:

```bash
export WHATSAPP_ACCESS_TOKEN="tu_token_aqui"
export WHATSAPP_PHONE_ID="tu_phone_id_aqui"
export GOOGLE_SHEET_ID="tu_sheet_id_aqui"
export WEBHOOK_VERIFY_TOKEN="mi_token_secreto_123"
```

### Opción 2: Editar directamente en app.py

Edita las líneas 9-12 en `app.py`:

```python
ACCESS_TOKEN = "TU_TOKEN_DE_META"
PHONE_ID = "TU_PHONE_NUMBER_ID"
SPREADSHEET_ID = "EL_ID_DE_TU_GOOGLE_SHEET"
WEBHOOK_VERIFY_TOKEN = "mi_token_secreto_123"
```

## 🏃 Ejecución

```bash
python app.py
```

El servidor se iniciará en `http://localhost:5000`

## 📱 Uso

1. Un usuario envía un mensaje de WhatsApp con un DNI (ej: `12345678`)
2. El bot busca el DNI en Google Sheets
3. Si encuentra el estudiante, responde con:
   - DNI
   - Nombre
   - Todas las notas disponibles (NOTA1, NOTA2, etc.)
4. Si no encuentra el DNI, envía un mensaje de error

## 🔍 Endpoints

- `POST /webhook` - Recibe mensajes de WhatsApp
- `GET /webhook` - Verificación del webhook
- `GET /health` - Verificar estado del servidor

## 🛠️ Solución de Problemas

### Error: "No se puede conectar a Google Sheets"
- Verifica que `credentials.json` esté en la carpeta del proyecto
- Asegúrate de haber compartido el Sheet con el email de la cuenta de servicio
- Verifica que el ID del Sheet sea correcto

### Error: "Error enviando mensaje WhatsApp"
- Verifica que el Access Token sea válido
- Asegúrate de que el Phone Number ID sea correcto
- Verifica que la API de WhatsApp esté habilitada

### El bot no responde
- Verifica que el webhook esté configurado correctamente
- Asegúrate de que el servidor esté ejecutándose
- Revisa los logs para ver errores

## 📝 Estructura del Proyecto

```
whatsApp-Bot-49/
├── app.py                 # Código principal del bot
├── requirements.txt       # Dependencias Python
├── credentials.json       # Credenciales de Google (NO subir a Git)
├── README.md             # Este archivo
└── .gitignore           # Archivos a ignorar (recomendado)
```

## 🔒 Seguridad

- ⚠️ **NO subas `credentials.json` a Git**
- ⚠️ **NO compartas tus tokens de acceso**
- ✅ Usa variables de entorno para tokens sensibles
- ✅ Crea un `.gitignore` para excluir archivos sensibles

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

