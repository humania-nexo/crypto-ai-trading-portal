"""
Technical Indicators Engine (Pure Pandas & NumPy).
Calculates essential trading indicators with high precision:
- EMAs (9, 20, 50, 200)
- RSI (Relative Strength Index)
- MACD (MACD line, Signal line, Histogram)
- ATR (Average True Range for dynamic SL/TP)
- Bollinger Bands (Upper, Middle, Lower, Bandwidth)
- Stochastic Oscillator (%K, %D)
- Volume Analysis (Volume MA, Volume Spikes)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

class TechnicalIndicators:
    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """Calcula todos los indicadores técnicos sobre un DataFrame con columnas [open, high, low, close, volume]."""
        df = df.copy()
        
        # 1. Medias Móviles Exponenciales (EMAs)
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # 2. RSI (Relative Strength Index - 14 periodos)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / (loss + 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 3. MACD (12, 26, 9)
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 4. ATR (Average True Range - 14 periodos para Stop Loss dinámico)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.ewm(alpha=1/14, adjust=False).mean()
        
        # 5. Bandas de Bollinger (20, 2)
        df['bb_mid'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_mid'] + (bb_std * 2)
        df['bb_lower'] = df['bb_mid'] - (bb_std * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / (df['bb_mid'] + 1e-10)
        
        # 6. Stochastic Oscillator (14, 3, 3)
        low_14 = df['low'].rolling(window=14).min()
        high_14 = df['high'].rolling(window=14).max()
        df['stoch_k'] = 100 * ((df['close'] - low_14) / ((high_14 - low_14) + 1e-10))
        df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
        
        # 7. Volumen y Volumen SMA (20)
        df['volume_sma20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / (df['volume_sma20'] + 1e-10)
        
        return df

    @staticmethod
    def get_latest_signal_summary(df: pd.DataFrame) -> Dict[str, Any]:
        """Extrae el estado del último candle con las señales cuantitativas calculadas."""
        if df.empty or len(df) < 50:
            return {}
            
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Tendencia basada en alineación de EMAs
        trend = "NEUTRAL"
        if last['close'] > last['ema_20'] > last['ema_50'] > last['ema_200']:
            trend = "STRONG_BULLISH"
        elif last['close'] > last['ema_20'] > last['ema_50']:
            trend = "BULLISH"
        elif last['close'] < last['ema_20'] < last['ema_50'] < last['ema_200']:
            trend = "STRONG_BEARISH"
        elif last['close'] < last['ema_20'] < last['ema_50']:
            trend = "BEARISH"
            
        # Cruce de MACD reciente
        macd_crossover = "NONE"
        if prev['macd'] <= prev['macd_signal'] and last['macd'] > last['macd_signal']:
            macd_crossover = "BULLISH_CROSS"
        elif prev['macd'] >= prev['macd_signal'] and last['macd'] < last['macd_signal']:
            macd_crossover = "BEARISH_CROSS"
            
        # Condición de RSI
        rsi_condition = "NORMAL"
        if last['rsi'] >= 70:
            rsi_condition = "OVERBOUGHT"
        elif last['rsi'] <= 30:
            rsi_condition = "OVERSOLD"
            
        # Detección de volumen anómalo (> 1.8x del promedio)
        volume_spike = bool(last['volume_ratio'] > 1.8)
        
        return {
            "close": float(last['close']),
            "trend": trend,
            "rsi": round(float(last['rsi']), 2),
            "rsi_condition": rsi_condition,
            "macd": round(float(last['macd']), 4),
            "macd_signal": round(float(last['macd_signal']), 4),
            "macd_hist": round(float(last['macd_hist']), 4),
            "macd_crossover": macd_crossover,
            "atr": round(float(last['atr']), 4),
            "bb_upper": round(float(last['bb_upper']), 2),
            "bb_lower": round(float(last['bb_lower']), 2),
            "volume_ratio": round(float(last['volume_ratio']), 2),
            "volume_spike": volume_spike,
            "ema_20": round(float(last['ema_20']), 2),
            "ema_50": round(float(last['ema_50']), 2),
            "ema_200": round(float(last['ema_200']), 2)
        }
