import requests

# CONFIGURACIÓN
TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"
MENSAJE = "✅ Prueba de conexión exitosa desde el bot."

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje
    }
    response = requests.post(url, data=data)
    print("Código de respuesta:", response.status_code)
    print("Respuesta:", response.json())

# Ejecutar prueba
enviar_telegram(MENSAJE)