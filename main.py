import requests, pandas as pd, ta, time, csv
from datetime import datetime
from flask import Flask
from threading import Thread

# CONFIGURACIÓN
API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "1min"
TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

PARES = [
    "EUR/USD", "EUR/CAD", "EUR/CHF", "EUR/GBP", "EUR/JPY",
    "AUD/CAD", "AUD/CHF", "AUD/USD", "AUD/JPY",
    "USD/CHF", "USD/JPY", "USD/INR", "USD/CAD",
    "GBP/JPY", "USD/BDT", "USD/MXN",
    "CAD/JPY", "GBP/CAD", "CAD/CHF", "NZD/CAD", "EUR/AUD"
]

ULTIMAS_SENIALES = {}

# FUNCIONES

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

def guardar_csv(fecha, par, tipo, estrategias, precio, expiracion):
    with open("senales_macd_cci.csv", "a", newline="") as f:
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
    return df

def analizar(symbol):
    df = obtener_datos(symbol)
    if df is None:
        return

    df["ema9"] = ta.trend.EMAIndicator(df["close"], 9).ema_indicator()
    df["ema20"] = ta.trend.EMAIndicator(df["close"], 20).ema_indicator()
    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["cci"] = ta.trend.CCIIndicator(df["close"], 20).cci()

    u = df.iloc[-1]
    a = df.iloc[-2]
    estrategias = []

    # 1. Cruce EMA
    if a["ema9"] < a["ema20"] and u["ema9"] > u["ema20"]:
        estrategias.append("Cruce EMA CALL")
    if a["ema9"] > a["ema20"] and u["ema9"] < u["ema20"]:
        estrategias.append("Cruce EMA PUT")

    # 2. MACD cruce
    if a["macd"] < a["macd_signal"] and u["macd"] > u["macd_signal"]:
        estrategias.append("MACD CALL")
    if a["macd"] > a["macd_signal"] and u["macd"] < u["macd_signal"]:
        estrategias.append("MACD PUT")

    # 3. CCI en zona
    if u["cci"] < -100:
        estrategias.append("CCI CALL")
    if u["cci"] > 100:
        estrategias.append("CCI PUT")

    if len(estrategias) >= 3:
        tipo = "CALL" if "CALL" in " ".join(estrategias) else "PUT"
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mensaje = (
            f"📊 Señal {tipo} en {symbol} ({fecha}):\n"
            + "\n".join(estrategias) +
            f"\n⏱️ Expiración sugerida: 5 min\n"
            f"📈 Confianza: ⭐⭐⭐"
        )
        enviar_telegram(mensaje)
        guardar_csv(fecha, symbol, tipo, ", ".join(estrategias), u["close"], "5 min")
        print(mensaje)
    else:
        print(f"[{symbol}] ❌ Sin señal clara")

def iniciar():
    while True:
        print("⏳ Analizando pares con EMA + MACD + CCI...")
        for par in PARES:
            analizar(par)
        print("🕒 Esperando 1 minuto...\n")
        time.sleep(60)

# FLASK (mantener activo en Render)
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot activo con estrategia: EMA + MACD + CCI (1min)"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
iniciar()
