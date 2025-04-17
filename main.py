import requests, pandas as pd, ta, time, csv
from datetime import datetime
from flask import Flask
from threading import Thread

# CONFIGURACIÓN
API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "1min"
TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

PARES = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CAD", "AUD/USD"]
ULTIMAS_SENIALES = {}

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

def guardar_csv(fecha, par, tipo, estrategias, precio, expiracion):
    with open("senales_parabolic_rsi.csv", "a", newline="") as f:
        csv.writer(f).writerow([fecha, par, tipo, estrategias, round(precio, 5), expiracion])

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

    df["sar"] = ta.trend.PSARIndicator(high=df["high"], low=df["low"], close=df["close"]).psar()
    df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()

    u = df.iloc[-1]
    estrategias = []

    # Estrategia: SAR + RSI
    if u["close"] > u["sar"] and u["rsi"] > 50:
        estrategias.append("Parabolic SAR + RSI CALL")
    elif u["close"] < u["sar"] and u["rsi"] < 50:
        estrategias.append("Parabolic SAR + RSI PUT")

    if estrategias:
        tipo = "CALL" if "CALL" in estrategias[0] else "PUT"
        clave = f"{symbol}_{tipo}"
        if ULTIMAS_SENIALES.get(symbol) == clave:
            print(f"[{symbol}] ⛔ Señal repetida, ignorada")
            return
        ULTIMAS_SENIALES[symbol] = clave

        fuerza = len(estrategias)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mensaje = (
            f"⚡ Señal {tipo} en {symbol}\n"
            + "\n".join(estrategias) +
            f"\n⏱️ Expiración sugerida: 1 min\n"
            f"🕒 {fecha}"
        )
        enviar_telegram(mensaje)
        guardar_csv(fecha, symbol, tipo, ", ".join(estrategias), u["close"], "1 min")
        print(mensaje)
    else:
        print(f"[{symbol}] ❌ Sin señal clara")

def iniciar():
    while True:
        print("🔁 Analizando todos los pares...")
        for par in PARES:
            analizar(par)
        print("🕐 Esperando 1 minuto...\n")
        time.sleep(60)

# Flask para mantener activo en Render
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot activo con estrategia: Parabolic SAR + RSI (cada 1 min)"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
iniciar()
