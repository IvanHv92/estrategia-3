import requests
import pandas as pd
import ta
import time
from datetime import datetime
from flask import Flask
from threading import Thread

# CONFIGURACIÓN
API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "2min"
TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

CRIPTOS = ["BTC/USD", "ETH/USD", "XRP/USD", "SOL/USD", "BNB/USD", "ADA/USD"]

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot Cripto | Breakout + Divergencia RSI activo."

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=data)

def obtener_datos(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={INTERVAL}&outputsize=100&apikey={API_KEY}"
    r = requests.get(url).json()
    if "values" not in r:
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
    if df is None or len(df) < 25:
        return

    df["ema20"] = ta.trend.EMAIndicator(df["close"], 20).ema_indicator()
    df["ema50"] = ta.trend.EMAIndicator(df["close"], 50).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], 14).rsi()
    bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()

    u = df.iloc[-1]
    a = df.iloc[-2]
    mensaje = None
    estrategia_activada = None

    # Estrategia 1: Breakout + impulso
    if a["ema20"] < a["ema50"] and u["ema20"] > u["ema50"] and u["rsi"] > 60 and u["close"] > a["close"]:
        mensaje = (
            f"🟢 *SEÑAL CALL - {symbol}*\n\n"
            f"✅ Activó: *Breakout + Impulso*\n"
            f"🔹 EMA20 cruzó EMA50 al alza\n"
            f"🔹 RSI: {round(u['rsi'], 2)}\n"
            f"🔹 Cierre superior a la vela previa\n\n"
            f"⏱️ Expiración sugerida: 3-5 min"
        )
        estrategia_activada = True

    elif a["ema20"] > a["ema50"] and u["ema20"] < u["ema50"] and u["rsi"] < 40 and u["close"] < a["close"]:
        mensaje = (
            f"🔴 *SEÑAL PUT - {symbol}*\n\n"
            f"✅ Activó: *Breakout + Impulso*\n"
            f"🔹 EMA20 cruzó EMA50 a la baja\n"
            f"🔹 RSI: {round(u['rsi'], 2)}\n"
            f"🔹 Cierre inferior a la vela previa\n\n"
            f"⏱️ Expiración sugerida: 3-5 min"
        )
        estrategia_activada = True

    # Estrategia 2: Bollinger Bands + divergencia RSI
    if not estrategia_activada:
        rsi = df["rsi"]
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # Divergencia bajista (precio hace nuevo máximo pero RSI no)
        if close.iloc[-1] > df["bb_upper"].iloc[-1] and rsi.iloc[-1] < rsi.iloc[-2] and close.iloc[-1] > close.iloc[-2]:
            mensaje = (
                f"🔴 *SEÑAL PUT - {symbol}*\n\n"
                f"✅ Activó: *Bollinger + Divergencia RSI*\n"
                f"🔹 Precio tocó banda superior\n"
                f"🔹 RSI no confirma nuevo máximo\n"
                f"🔹 RSI actual: {round(rsi.iloc[-1], 2)}\n\n"
                f"⏱️ Expiración sugerida: 3-5 min"
            )

        # Divergencia alcista (precio hace nuevo mínimo pero RSI no)
        elif close.iloc[-1] < df["bb_lower"].iloc[-1] and rsi.iloc[-1] > rsi.iloc[-2] and close.iloc[-1] < close.iloc[-2]:
            mensaje = (
                f"🟢 *SEÑAL CALL - {symbol}*\n\n"
                f"✅ Activó: *Bollinger + Divergencia RSI*\n"
                f"🔹 Precio tocó banda inferior\n"
                f"🔹 RSI no confirma nuevo mínimo\n"
                f"🔹 RSI actual: {round(rsi.iloc[-1], 2)}\n\n"
                f"⏱️ Expiración sugerida: 3-5 min"
            )

    if mensaje:
        enviar_telegram(mensaje)
        print(f"✅ Señal enviada: {symbol}")
    else:
        print(f"❌ Sin señal clara: {symbol}")

def ejecutar_bot():
    while True:
        for par in CRIPTOS:
            analizar(par)
        print("⏳ Esperando 2 minutos...\n")
        time.sleep(120)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    ejecutar_bot()
