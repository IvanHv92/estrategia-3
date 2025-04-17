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
    "GBP/JPY", "USD/BDT", "USD/MXN", "CAD/JPY", "GBP/CAD",
    "CAD/CHF", "NZD/CAD", "EUR/AUD"
]

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

def guardar_csv(fecha, par, tipo, estrategia, precio):
    with open("senales_alligator_macd.csv", "a", newline="") as f:
        csv.writer(f).writerow([fecha, par, tipo, estrategia, round(precio, 5)])

def obtener_datos(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={INTERVAL}&outputsize=100&apikey={API_KEY}"
    r = requests.get(url).json()
    if "values" not in r:
        print(f"❌ Error con {symbol}")
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

    # Alligator (tres EMAs con periodos diferentes)
    df["jaw"] = ta.trend.SMAIndicator(df["close"], 13).sma_indicator()
    df["teeth"] = ta.trend.SMAIndicator(df["close"], 8).sma_indicator()
    df["lips"] = ta.trend.SMAIndicator(df["close"], 5).sma_indicator()

    # MACD
    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    u = df.iloc[-1]
    a = df.iloc[-2]

    estrategia = None
    tipo = None

    # Condición Alligator (cruce de medias y separación ordenada)
    alligator_call = a["lips"] < a["teeth"] < a["jaw"] and u["lips"] > u["teeth"] > u["jaw"]
    alligator_put = a["lips"] > a["teeth"] > a["jaw"] and u["lips"] < u["teeth"] < u["jaw"]

    # Condición MACD
    macd_call = a["macd"] < a["macd_signal"] and u["macd"] > u["macd_signal"]
    macd_put = a["macd"] > a["macd_signal"] and u["macd"] < u["macd_signal"]

    if alligator_call and macd_call:
        estrategia = "Alligator + MACD CALL"
        tipo = "CALL"
    elif alligator_put and macd_put:
        estrategia = "Alligator + MACD PUT"
        tipo = "PUT"

    if estrategia:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mensaje = (
            f"📊 Señal {tipo} en {symbol} ({fecha}):\n"
            f"{estrategia}\n"
            f"⏱️ Expiración sugerida: 5 min\n"
            f"📈 Confianza: ⭐⭐"
        )
        enviar_telegram(mensaje)
        guardar_csv(fecha, symbol, tipo, estrategia, u["close"])
        print(mensaje)
    else:
        print(f"[{symbol}] ❌ Sin señal clara")

def iniciar():
    while True:
        print("\n🔁 Analizando pares con Alligator + MACD...\n")
        for par in PARES:
            analizar(par)
        print("🕒 Esperando 1 minuto...\n")
        time.sleep(60)

# Flask para mantener activo en Render
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot activo con estrategia: Alligator + MACD (velas 1 min, expiración 5 min)"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
iniciar()
