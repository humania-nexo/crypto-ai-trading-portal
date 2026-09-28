"""
Technical Analysis Agent.
Coordinates data retrieval via CCXT and Binance Public Data Vision API (Global, no geo-blocking)
and computes technical indicators and pattern recognition.
"""

import ccxt
import requests
import pandas as pd
import logging
from typing import Dict, Any, List, Optional
from src.analysis.indicators import TechnicalIndicators
from src.analysis.patterns import PatternDetector

logger = logging.getLogger(__name__)

class TechnicalAgent:
    def __init__(self, exchange_id: str = "binance"):
        self.exchange_id = exchange_id
        if exchange_id == "binance":
            # Usar endpoint oficial global data-api.binance.vision que permite lectura de datos desde cualquier servidor (EE.UU., Europa, etc.)
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot', 'adjustForTimeDifference': True},
                'urls': {
                    'api': {
                        'public': 'https://data-api.binance.vision/api/v3',
                        'v3': 'https://data-api.binance.vision/api/v3',
                    }
                }
            })
        else:
            self.exchange = getattr(ccxt, exchange_id)({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })

    def fetch_ohlcv(self, symbol: str = "BTC/USDT", timeframe: str = "15m", limit: int = 100) -> pd.DataFrame:
        """Descarga velas japonesas en tiempo real desde el exchange con soporte antibloqueo geográfico."""
        # 1. Intentar vía CCXT configurado con data-api
        try:
            raw_candles = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if raw_candles and len(raw_candles) > 0:
                df = pd.DataFrame(raw_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df
        except Exception as e:
            logger.warning(f"CCXT fetch_ohlcv falló para {symbol}: {e}. Intentando fallback directo vía Binance Data API...")

        # 2. Fallback Directo vía REST API a data-api.binance.vision (100% libre de restricciones en la nube)
        try:
            raw_symbol = symbol.replace("/", "")
            url = "https://data-api.binance.vision/api/v3/klines"
            params = {
                "symbol": raw_symbol,
                "interval": timeframe,
                "limit": limit
            }
            resp = requests.get(url, params=params, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                parsed = []
                for k in data:
                    parsed.append([
                        int(k[0]),        # Open time
                        float(k[1]),      # Open
                        float(k[2]),      # High
                        float(k[3]),      # Low
                        float(k[4]),      # Close
                        float(k[5])       # Volume
                    ])
                df = pd.DataFrame(parsed, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df
        except Exception as e_rest:
            logger.error(f"Fallback REST falló para {symbol}: {e_rest}")

        return pd.DataFrame()

    def analyze_pair(self, symbol: str = "BTC/USDT", timeframe: str = "15m") -> Dict[str, Any]:
        """Realiza el análisis técnico completo de un par (Indicadores + Velas + Figuras Chartistas)."""
        df = self.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=120)
        if df.empty or len(df) < 50:
            return {"status": "error", "message": f"Insuficientes datos para {symbol}"}
            
        df_indicators = TechnicalIndicators.calculate_all(df)
        signals = TechnicalIndicators.get_latest_signal_summary(df_indicators)
        candlestick_patterns = PatternDetector.identify_candlestick_patterns(df_indicators)
        chart_formations = PatternDetector.identify_chart_formations(df_indicators)
        levels = PatternDetector.calculate_historical_supports_resistances(df_indicators)
        
        # Scoring técnico (-1.0 a +1.0)
        score = 0.0
        
        # 1. Tendencia
        if signals.get("trend") == "STRONG_BULLISH":
            score += 0.35
        elif signals.get("trend") == "BULLISH":
            score += 0.20
        elif signals.get("trend") == "STRONG_BEARISH":
            score -= 0.40
        elif signals.get("trend") == "BEARISH":
            score -= 0.20
            
        # 2. MACD
        if signals.get("macd_crossover") == "BULLISH_CROSS":
            score += 0.25
        elif signals.get("macd_crossover") == "BEARISH_CROSS":
            score -= 0.25
            
        # 3. RSI
        rsi_val = signals.get("rsi", 50)
        if 40 <= rsi_val <= 60:
            score += 0.15 # Zona neutral saludable
        elif rsi_val < 30:
            score += 0.20 # Sobrevendido (Oportunidad de rebote)
        elif rsi_val > 70:
            score -= 0.20 # Sobrecomprado
            
        # 4. Formaciones Chartistas
        for f in chart_formations:
            if "ALCISTA" in f.get("type", ""):
                score += 0.25
            elif "BAJISTA" in f.get("type", ""):
                score -= 0.25
                
        # 5. Patrones de Velas
        for c in candlestick_patterns:
            if c.get("bias") == "BULLISH":
                score += 0.15
            elif c.get("bias") == "BEARISH":
                score -= 0.15
                
        # Normalizar score entre -1.0 y 1.0
        score = max(-1.0, min(1.0, score))
        
        bias = "NEUTRAL"
        if score >= 0.35:
            bias = "STRONG_BULLISH"
        elif score >= 0.15:
            bias = "BULLISH"
        elif score <= -0.35:
            bias = "STRONG_BEARISH"
        elif score <= -0.15:
            bias = "BEARISH"
            
        all_patterns = candlestick_patterns + chart_formations
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "status": "success",
            "price": float(df['close'].iloc[-1]),
            "current_price": float(df['close'].iloc[-1]),
            "technical_score": round(score, 2),
            "score": round(score, 2),
            "bias": bias,
            "signals": signals,
            "patterns": all_patterns,
            "candlestick_patterns": candlestick_patterns,
            "chart_formations": chart_formations,
            "levels": levels,
            "supports_resistances": levels,
            "df": df_indicators
        }
