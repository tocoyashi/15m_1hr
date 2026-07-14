import os
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import ccxt
import pandas as pd
import ta
import requests
import time
import random

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

TIMEFRAME = "15m"
TIMEFRAME_H1 = "1h"

# ========== 38 عملة ==========
SYMBOLS = [
    "BTC/USDT", "ADA/USDT", "DOGE/USDT", "TRX/USDT", "AVAX/USDT",
    "LINK/USDT", "DOT/USDT", "POL/USDT", "SHIB/USDT", "LTC/USDT",
    "UNI/USDT", "ATOM/USDT", "XLM/USDT", "NEAR/USDT", "APT/USDT",
    "ARB/USDT", "OP/USDT", "INJ/USDT", "AAVE/USDT",
    "GRT/USDT", "FET/USDT", "FLOKI/USDT", "WIF/USDT",
    "SEI/USDT", "ICP/USDT", "WLD/USDT", "IMX/USDT", "RENDER/USDT",
    "JUP/USDT", "STRK/USDT", "BONK/USDT", "ONDO/USDT", "PYTH/USDT",
    "ENA/USDT", "ORDI/USDT", "KAS/USDT"
]


def get_decimals(price):
    if price > 100: return 2
    elif price > 1: return 3
    elif price > 0.01: return 5
    else: return 8


def get_next_signal_id():
    filename = "signal_counter_15m.txt"
    try:
        with open(filename, "r") as file:
            current_id = int(file.read().strip())
    except (FileNotFoundError, ValueError):
        current_id = 0
    next_id = current_id + 1
    try:
        with open(filename, "w") as file:
            file.write(str(next_id))
    except Exception as e:
        print(f"Error saving signal ID: {e}")
    return f"{next_id:03d}"


def strength_bar(score):
    filled = max(1, min(5, round(score / 20)))
    colors = ['\U0001f7e5', '\U0001f7e7', '\U0001f7e8', '\U0001f7e9', '\U0001f7e9']
    empty = '\u2b1c\ufe0f'
    return ''.join(colors[i] for i in range(filled)) + empty * (5 - filled)


def generate_summary(direction, strategy, df):
    return ""


def send_crypto_signal(coin_name, direction, strategy, entry, leverage, tp1, tp2, tp3, tp4, sl, summary_text, strength=50):
    signal_id = get_next_signal_id()
    direction_text = "LONG" if direction.lower() == "long" else "SHORT"
    clean_name = coin_name.replace("/", "")
    dec = get_decimals(entry)

    zone_low = round(entry * 0.9985, dec)
    zone_high = round(entry * 1.0015, dec)

    is_long = direction.lower() == "long"
    arrow_emoji = "⬆️" if is_long else "⬇️"

    if is_long:
        entry_low, entry_high = zone_low, zone_high
    else:
        entry_low, entry_high = zone_high, zone_low

    text = (
        f"👁‍🗨 {strategy}  \n\n"
        f"☰ #{clean_name}  │  M15 + H1\n"
        f"☰ {direction_text} : {entry_low} - {entry_high}  {arrow_emoji}\n"
        f"☰ Leverage:  {leverage}x\n\n"
        f"► TP 1: {tp1}\n"
        f"► TP 2: {tp2}\n"
        f"► TP 3: {tp3}\n"
        f"► TP 4: {tp4}\n\n"
        f"✖️ Stop-Loss: {sl}\n"
        f"🟰 After TP1 → SL to BE\n\n"
        f"»»---------------------------------\n"
        f"Leaked By : Banana Bot"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "disable_web_page_preview": True}
    try:
        response = requests.post(url, json=payload)
        if response.json().get('ok'):
            print(f"Signal {signal_id} sent for {coin_name} via {strategy}")
        else:
            print(f"ERROR for {coin_name}: {response.json().get('description')}")
    except Exception as e:
        print(f"Network error: {e}")


def analyze_and_trade():
    print("Starting 15M Scalp Scan with H1 Confirmation & Volume Filter...")
    exchange = ccxt.mexc()

    for symbol in SYMBOLS:
        try:
            # ========== جلب بيانات M15 ==========
            ohlcv_15m = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
            df_15m = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            # ========== جلب بيانات H1 ==========
            ohlcv_h1 = exchange.fetch_ohlcv(symbol, TIMEFRAME_H1, limit=100)
            df_h1 = pd.DataFrame(ohlcv_h1, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            # ========== فلتر الحجم ==========
            avg_volume = df_15m['volume'].tail(20).mean()
            current_volume = df_15m['volume'].iloc[-1]

            if current_volume < avg_volume * 0.3:
                continue

            # ========== تحليل H1 (الاتجاه العام) ==========
            h1_ema50 = df_h1['close'].ewm(span=50, adjust=False).mean().iloc[-1]
            h1_close = df_h1['close'].iloc[-1]
            h1_trend_bullish = h1_close > h1_ema50
            h1_trend_bearish = h1_close < h1_ema50

            # ========== تحليل M15 ==========
            # Strategy 1: EMA Cross
            df_15m['ema_9'] = df_15m['close'].ewm(span=9, adjust=False).mean()
            df_15m['ema_21'] = df_15m['close'].ewm(span=21, adjust=False).mean()
            ema_buy = (df_15m['ema_9'].iloc[-2] < df_15m['ema_21'].iloc[-2]) and (df_15m['ema_9'].iloc[-1] > df_15m['ema_21'].iloc[-1])
            ema_sell = (df_15m['ema_9'].iloc[-2] > df_15m['ema_21'].iloc[-2]) and (df_15m['ema_9'].iloc[-1] < df_15m['ema_21'].iloc[-1])

            # Strategy 2: MACD Histogram Cross
            macd_hist = ta.trend.macd_diff(df_15m['close'])
            macd_buy = (macd_hist.iloc[-2] < 0) and (macd_hist.iloc[-1] > 0)
            macd_sell = (macd_hist.iloc[-2] > 0) and (macd_hist.iloc[-1] < 0)

            # Strategy 3: Bollinger Bands Breakout
            bb = ta.volatility.BollingerBands(close=df_15m['close'], window=20, window_dev=2)
            curr_upper = bb.bollinger_hband().iloc[-1]
            curr_lower = bb.bollinger_lband().iloc[-1]
            prev_upper = bb.bollinger_hband().iloc[-2]
            prev_lower = bb.bollinger_lband().iloc[-2]
            current_close = df_15m['close'].iloc[-1]

            bb_buy = (df_15m['close'].iloc[-2] <= prev_upper) and (current_close > curr_upper)
            bb_sell = (df_15m['close'].iloc[-2] >= prev_lower) and (current_close < curr_lower)

            decimals = get_decimals(current_close)

            # ========== فلتر H1 + إرسال الإشارات ==========

            # LONG Signals (H1 bullish)
            if (ema_buy or macd_buy or bb_buy) and h1_trend_bullish:
                strategy_name = "Golden Cross" if ema_buy else ("MACD" if macd_buy else "Breakout")
                lev = "15" if ema_buy else ("25" if macd_buy else "20")

                print(f"BUY on {symbol} via {strategy_name} ({lev}x) | H1 Confirmed!")
                entry = round(current_close, decimals)

                rsi = ta.momentum.rsi(df_15m['close'], window=14).iloc[-1]
                vol_ratio = current_volume / avg_volume
                strength = min(100, abs(rsi - 50) * 1.5 + vol_ratio * 10 + 30)

                summary = generate_summary("LONG", strategy_name, df_15m)

                send_crypto_signal(symbol, "LONG", strategy_name, entry, lev,
                    round(entry * 1.0075, decimals), round(entry * 1.017, decimals),
                    round(entry * 1.032, decimals), round(entry * 1.058, decimals),
                    round(entry * 0.95, decimals), summary, strength)
                time.sleep(6)

            # SHORT Signals (H1 bearish)
            elif (ema_sell or macd_sell or bb_sell) and h1_trend_bearish:
                strategy_name = "Golden Cross" if ema_sell else ("MACD" if macd_sell else "Breakdown")
                lev = "15" if ema_sell else ("25" if macd_sell else "20")

                print(f"SELL on {symbol} via {strategy_name} ({lev}x) | H1 Confirmed!")
                entry = round(current_close, decimals)

                rsi = ta.momentum.rsi(df_15m['close'], window=14).iloc[-1]
                vol_ratio = current_volume / avg_volume
                strength = min(100, abs(rsi - 50) * 1.5 + vol_ratio * 10 + 30)

                summary = generate_summary("SHORT", strategy_name, df_15m)

                send_crypto_signal(symbol, "SHORT", strategy_name, entry, lev,
                    round(entry * 0.9925, decimals), round(entry * 0.983, decimals),
                    round(entry * 0.968, decimals), round(entry * 0.942, decimals),
                    round(entry * 1.05, decimals), summary, strength)
                time.sleep(6)

        except Exception as e:
            print(f"Error {symbol}: {e}")


if __name__ == "__main__":
    print("15M Scalp Bot with H1 Confirmation started...")
    analyze_and_trade()
