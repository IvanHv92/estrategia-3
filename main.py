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
    "GBP/JPY", "USD/BDT", "USD/MXN", "CAD/JPY",
    "GBP/CAD", "CAD/CHF", "NZD/CAD", "EUR/AUD"
]

ULTIMAS_SENIALES = {}


def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)


def guardar_csv(fecha, par, tipo, estrategias, precio, expiracion):
    with open("senales_cci.csv", "a", newline="") as f:
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

    df["macd"] = ta.trend.MACD(df["close"]).macd()
    df["macd_signal"] = ta.trend.MACD(df["close"]).macd_signal()
    df["cci"] = ta.momentum.CCIIndicator(df["high"], df["low"], df["close"], 20).cci()
    df["ema20"] = ta.trend.EMAIndicator(df["close"], 20).ema_indicator()

    u = df.iloc[-1]
    a = df.iloc[-2]

    estrategias = []

    if a["macd"] < a["macd_signal"] and u["macd"] > u["macd_signal"]:
        estrategias.append("MACD cruce alcista")
    if a["macd"] > a["macd_signal"] and u["macd"] < u["macd_signal"]:
        estrategias.append("MACD cruce bajista")

    if u["cci"] > 100:
        estrategias.append("CCI sobrecomprado")
    elif u["cci"] < -100:
        estrategias.append("CCI sobrevendido")

    if u["close"] > u["ema20"]:
        estrategias.append("Precio sobre EMA")
    elif u["close"] < u["ema20"]:
        estrategias.append("Precio bajo EMA")

    call = ["MACD cruce alcista", "CCI sobrevendido", "Precio sobre EMA"]
    put = ["MACD cruce bajista", "CCI sobrecomprado", "Precio bajo EMA"]

    if all(e in estrategias for e in call):
        tipo = "CALL"
    elif all(e in estrategias for e in put):
        tipo = "PUT"
    else:
        print(f"[{symbol}] ❌ Sin condiciones completas")
        return

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


def iniciar():
    while True:
        print("⏳ Analizando todos los pares...")
        for par in PARES:
            analizar(par)
        print("🕒 Esperando 2 minutos...\n")
        time.sleep(120)


app = Flask('')


@app.route('/')
def home():
    return "✅ Bot activo con estrategia: MACD + CCI + EMA (1min, cada 2min)"


Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
iniciar()