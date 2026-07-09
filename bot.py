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
    "SUI/USDT", "ARB/USDT", "OP/USDT", "INJ/USDT", "AAVE/USDT",
    "GRT/USDT", "PEPE/USDT", "FET/USDT", "FLOKI/USDT", "WIF/USDT",
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

# ========== تحليل بدون أرقام ==========
def generate_summary(direction, strategy, df):
    rsi_val = round(ta.momentum.rsi(df['close'], window=14).iloc[-1], 1)

    # الهيكل السعري (بدون أرقام)
    if df['close'].iloc[-1] > df['close'].ewm(span=50, adjust=False).mean().iloc[-1]:
        structure_txt = random.choice([
            "The intraday chart maintains a bullish posture with price holding above dynamic support.",
            "Short-term structure favors buyers as momentum sustains above key averages.",
            "Price action on the fifteen-minute frame reflects steady bullish commitment."
        ])
    else:
        structure_txt = random.choice([
            "The intraday chart maintains a bearish posture with price holding below dynamic resistance.",
            "Short-term structure favors sellers as momentum sustains below key averages.",
            "Price action on the fifteen-minute frame reflects steady bearish commitment."
        ])

    # الحدث المُفَعِّل (بدون أرقام)
    if "Golden" in strategy:
        if direction == "LONG":
            action_txt = random.choice([
                "A fast exponential crossover has triggered fresh buying interest.",
                "Short-term averages aligned bullishly, opening a momentum scalp window.",
                "Price reclaimed the fast average, signaling a shift in micro-structure."
            ])
        else:
            action_txt = random.choice([
                "A fast exponential crossover has triggered fresh selling interest.",
                "Short-term averages aligned bearishly, opening a momentum scalp window.",
                "Price lost the fast average, signaling a shift in micro-structure."
            ])
    elif "Divergence" in strategy:
        if direction == "LONG":
            action_txt = random.choice([
                "The momentum oscillator turned positive, confirming a bullish divergence.",
                "A fresh bullish cross on the momentum gauge suggests accelerating upside.",
                "Buying pressure intensified as the histogram flipped into positive territory."
            ])
        else:
            action_txt = random.choice([
                "The momentum oscillator turned negative, confirming a bearish divergence.",
                "A fresh bearish cross on the momentum gauge suggests accelerating downside.",
                "Selling pressure intensified as the histogram flipped into negative territory."
            ])
    else:  # BB
        if direction == "LONG":
            action_txt = random.choice([
                "An expansion beyond the upper volatility band signals a breakout impulse.",
                "Price stretched above the compression zone, indicating a volatility surge.",
                "The squeeze resolved to the upside with aggressive momentum."
            ])
        else:
            action_txt = random.choice([
                "An expansion beyond the lower volatility band signals a breakdown impulse.",
                "Price stretched below the compression zone, indicating a volatility surge.",
                "The squeeze resolved to the downside with aggressive momentum."
            ])

    # الزخم (وصف فقط، بدون ذكر الرقم)
    if direction == "LONG":
        if rsi_val < 70:
            rsi_txt = random.choice([
                "Momentum remains healthy with room before reaching extreme overbought conditions.",
                "The oscillator shows constructive buying pressure without overheating.",
                "Buyers maintain control as the momentum gauge sits in a sustainable zone."
            ])
        else:
            rsi_txt = random.choice([
                "Momentum is running hot, riding strong overbought conditions.",
                "The oscillator shows intense buying pressure at elevated levels.",
                "Buyers dominate with the momentum gauge deep in the upper extreme."
            ])
    else:
        if rsi_val > 30:
            rsi_txt = random.choice([
                "Momentum remains healthy with room before reaching extreme oversold conditions.",
                "The oscillator shows constructive selling pressure without capitulation.",
                "Sellers maintain control as the momentum gauge sits in a sustainable zone."
            ])
        else:
            rsi_txt = random.choice([
                "Momentum is running cold, riding strong oversold conditions.",
                "The oscillator shows intense selling pressure at depressed levels.",
                "Sellers dominate with the momentum gauge deep in the lower extreme."
            ])

    # مستويات المخاطر (بدون أرقام!)
    if direction == "LONG":
        levels_txt = random.choice([
            "Invalidation lies below the entry zone; target a quick sweep to the first objective and extension toward the final target.",
            "Risk is strictly managed beneath the entry area; expect a rapid move to secure initial profits.",
            "Place defensive stops below the setup zone; anticipate swift execution toward the nearest target."
        ])
    else:
        levels_txt = random.choice([
            "Invalidation lies above the entry zone; target a quick drop to the first objective and extension toward the final target.",
            "Risk is strictly managed above the entry area; expect a rapid move to secure initial profits.",
            "Place defensive stops above the setup zone; anticipate swift execution toward the nearest target."
        ])

    summary = f"{structure_txt} {action_txt} {rsi_txt} {levels_txt}"
    return summary

def send_crypto_signal(coin_name, direction, strategy, entry, leverage, tp1, tp2, tp3, tp4, sl, summary_text):
    signal_id = get_next_signal_id()
    direction_text = "Long" if direction.lower() == "long" else "Short"
    clean_name = coin_name.replace("/", "")

    zone_low = round(entry * 0.9985, get_decimals(entry))
    zone_high = round(entry * 1.0015, get_decimals(entry))

    arrow = "⇈" if direction.lower() == "long" else "⇊"

    text = f"""📌 Signal Strat: {strategy}
➕ #{clean_name} {TIMEFRAME.upper()} | {TIMEFRAME_H1.upper()}
➕ {direction_text} Entry Zone: {zone_low} - {zone_high} {arrow}
➕ Leverage: {leverage}x

📌 Strategy Details:
➕ TP 1: {tp1}
➕ TP 2: {tp2}
➕ TP 3: {tp3}
➕ TP 4: {tp4}

🔻 Stop-Loss: {sl}
🔻 After TP1 move SL to BE

———————————

✂️ {summary_text}"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "disable_web_page_preview": True, "parse_mode": "HTML"}
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
                print(f"Volume filter rejected {symbol}: current={current_volume:.0f} < 30% of avg(20)={avg_volume:.0f}")
                continue

            # ========== تحليل H1 (الاتجاه العام) ==========
            h1_ema50 = df_h1['close'].ewm(span=50, adjust=False).mean().iloc[-1]
            h1_close = df_h1['close'].iloc[-1]
            h1_trend_bullish = h1_close > h1_ema50
            h1_trend_bearish = h1_close < h1_ema50

            # ========== تحليل M15 ==========
            # Strategy 1: EMA
            df_15m['ema_9'] = df_15m['close'].ewm(span=9, adjust=False).mean()
            df_15m['ema_21'] = df_15m['close'].ewm(span=21, adjust=False).mean()
            ema_buy = (df_15m['ema_9'].iloc[-2] < df_15m['ema_21'].iloc[-2]) and (df_15m['ema_9'].iloc[-1] > df_15m['ema_21'].iloc[-1])
            ema_sell = (df_15m['ema_9'].iloc[-2] > df_15m['ema_21'].iloc[-2]) and (df_15m['ema_9'].iloc[-1] < df_15m['ema_21'].iloc[-1])

            # Strategy 2: MACD
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

            # ✨ LONG Signals (H1 صاعد)
            if (ema_buy or macd_buy or bb_buy) and h1_trend_bullish:
                strategy_name = "Golden Cross" if ema_buy else ("M Divergence" if macd_buy else "Breakout")
                lev = "15" if ema_buy else ("25" if macd_buy else "20")

                print(f"BUY on {symbol} via {strategy_name} ({lev}x) | H1 Confirmed!")
                entry = round(current_close, decimals)

                summary = generate_summary("LONG", strategy_name, df_15m)

                send_crypto_signal(symbol, "LONG", strategy_name, entry, lev, 
                    round(entry * 1.0075, decimals), round(entry * 1.017, decimals), 
                    round(entry * 1.032, decimals), round(entry * 1.058, decimals), 
                    round(entry * 0.95, decimals), summary)
                time.sleep(6)

            # ✨ SHORT Signals (H1 هابط)
            elif (ema_sell or macd_sell or bb_sell) and h1_trend_bearish:
                strategy_name = "Golden Cross" if ema_sell else ("M Divergence" if macd_sell else "Breakdown")
                lev = "15" if ema_sell else ("25" if macd_sell else "20")

                print(f"SELL on {symbol} via {strategy_name} ({lev}x) | H1 Confirmed!")
                entry = round(current_close, decimals)

                summary = generate_summary("SHORT", strategy_name, df_15m)

                send_crypto_signal(symbol, "SHORT", strategy_name, entry, lev, 
                    round(entry * 0.9925, decimals), round(entry * 0.983, decimals), 
                    round(entry * 0.968, decimals), round(entry * 0.942, decimals), 
                    round(entry * 1.05, decimals), summary)
                time.sleep(6)
            else:
                if (ema_buy or macd_buy or bb_buy or ema_sell or macd_sell or bb_sell):
                    print(f"H1 filter rejected {symbol}: M15 signal present but H1 trend mismatch")

        except Exception as e:
            print(f"Error {symbol}: {e}")

if __name__ == "__main__":
    print("15M Scalp Bot with H1 Confirmation started...")
    analyze_and_trade()
