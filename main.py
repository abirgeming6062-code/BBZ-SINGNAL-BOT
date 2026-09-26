import asyncio
import json
import pandas as pd
import ta
import requests
from fastapi import FastAPI, WebSocket
import datetime

app = FastAPI()

def get_quotex_data():
    try:
        # Quotex কারেন্সি পেয়ার ওটিসি মুভমেন্ট ট্র্যাক করার জন্য লাইভ ফিড এপিআই
        url = "https://binance.com"
        response = requests.get(url).json()
        closes = [float(candle[4]) for candle in response]
        highs = [float(candle[2]) for candle in response]
        lows = [float(candle[3]) for candle in response]
        return pd.DataFrame({'close': closes, 'high': highs, 'low': lows})
    except:
        return None

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    step = 1
    
    while True:
        try:
            df = get_quotex_data()
            signal = "WAIT"
            
            if df is not None and len(df) >= 20:
                # টেকনিক্যাল ফিল্টার ক্যালকুলেশন
                df['rsi'] = ta.momentum.rsi(df['close'], window=14)
                indicator_bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
                bb_high = indicator_bb.bollinger_hband().iloc[-1]
                bb_low = indicator_bb.bollinger_lband().iloc[-1]
                
                last_close = df['close'].iloc[-1]
                last_rsi = df['rsi'].iloc[-1]
                
                # হাই-কনফিডেন্স বাইনারি অপশন এন্ট্রি লজিক
                if last_close <= bb_low and last_rsi < 35:
                    signal = "UP"
                elif last_close >= bb_high and last_rsi > 65:
                    signal = "DOWN"

            # ওটিসি ১ মিনিটের ক্যান্ডেল টাইমার ট্র্যাকিং
            seconds_left = 60 - datetime.datetime.now().second
            
            # প্রতি নতুন ১ মিনিটের শুরুতে ক্যান্ডেল পরিবর্তন হলে মার্টিনগেল স্টেপ বাড়বে
            if seconds_left >= 59:
                step = step + 1 if step < 5 else 1

            await websocket.send_text(json.dumps({
                "signal": signal,
                "timer": f"00:{seconds_left:02d}",
                "step": f"STEP {step}/5"
            }))
            await asyncio.sleep(1)
            
        except Exception as e:
            break
