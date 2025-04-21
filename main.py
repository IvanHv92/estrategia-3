import requests
import pandas as pd
import ta
import time
from datetime import datetime
from threading import Thread
from flask import Flask

# CONFIGURACIÓN GENERAL
API_KEY = "TU_API_KEY_DE_TWELVE_DATA"
INTERVAL = "1min"
TELEGRAM_TOKEN = "TU_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "TU_TELEGRAM_CHAT_ID"

CRIPTO_PRINCIPALES = [
    "BTC/USD", "ETH/USD", "XRP/USD", "BNB/USD", "ADA/USD",
    "DOGE/USD", "SOL/USD", "AVAX/USD", "DOT/USD", "LTC/USD"
]

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot Cripto Eficiente Activo"

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")

def obtener_datos(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={INTERVAL}&outputsize=100&apikey={API_KEY}"
    r = requests.get(url).json()
    if "values" not in r:
        print(f"❌ Error al obtener datos de {symbol}")
        return None
    df = pd.DataFrame(r["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df

def analizar(symbol):
    df = obtener_datos(symbol)
    if df is None:
        return

    df["rsi"] = ta.momentum.RSIIndicator(df["close"], 14).rsi()
    df["cci"] = ta.trend.CCIIndicator(df["high"], df["low"], df["close"], 20).cci()
    df["ema"] = ta.trend.EMAIndicator(df["close"], 21).ema_indicator()

    u = df.iloc[-1]
    a = df.iloc[-2]
    rsi_val = round(u["rsi"], 2)
    cci_val = round(u["cci"], 2)
    ema = u["ema"]
    precio = u["close"]

    mensaje = None

    # Señal de COMPRA (CALL)
    if rsi_val < 28 and cci_val < -120 and precio > ema and precio > a["close"]:
        mensaje = (
            f"🟢 *SEÑAL CALL (Compra)*\n\n"
            f"🔹 *Cripto:* {symbol}\n"
            f"📊 RSI: {rsi_val}  |  CCI: {cci_val}\n"
            f"📈 Precio: {round(precio, 2)} | EMA21: {round(ema, 2)}\n\n"
            f"✅ Confirmación alcista tras sobreventa\n"
            f"⏱️ *Velas:* 1 minuto | Expiración sugerida: 2-3 min"
        )

    # Señal de VENTA (PUT)
    elif rsi_val > 72 and cci_val > 120 and precio < ema and precio < a["close"]:
        mensaje = (
            f"🔴 *SEÑAL PUT (Venta)*\n\n"
            f"🔹 *Cripto:* {symbol}\n"
            f"📊 RSI: {rsi_val}  |  CCI: {cci_val}\n"
            f"📉 Precio: {round(precio, 2)} | EMA21: {round(ema, 2)}\n\n"
            f"✅ Confirmación bajista tras sobrecompra\n"
            f"⏱️ *Velas:* 1 minuto | Expiración sugerida: 2-3 min"
        )

    if mensaje:
        enviar_telegram(mensaje)
        print(f"✅ Señal enviada: {symbol}")
    else:
        print(f"❌ Sin señal clara: {symbol}")

def ejecutar_bot():
    while True:
        for cripto in CRIPTO_PRINCIPALES:
            analizar(cripto)
        print("⏳ Esperando 60 segundos...\n")
        time.sleep(60)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    ejecutar_bot()
