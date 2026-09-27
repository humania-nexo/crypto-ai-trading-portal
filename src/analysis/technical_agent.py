"""
Technical Analysis Agent.
Coordinates data retrieval via CCXT (Binance) and computes technical indicators and pattern recognition.
"""

import ccxt
import pandas as pd
import logging
from typing import Dict, Any, List, Optional
from src.analysis.indicators import TechnicalIndicators
from src.analysis.patterns import PatternDetector

logger = logging.getLogger(__name__)

class TechnicalAgent:
    def __init__(self, exchange_id: str = "binance"):
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })

    def fetch_ohlcv(self, symbol: str = "BTC/USDT", timeframe: str = "15m", limit: int = 100) -> pd.DataFrame:
        """Descarga velas japonesas en tiempo real desde el exchange."""
        try:
            raw_candles = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(raw_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol} ({timeframe}): {e}")
            return pd.DataFrame()

    def analyze_pair(self, symbol: str = "BTC/USDT", timeframe: str = "15m") -> Dict[str, Any]:
        """Realiza el análisis técnico completo de un par."""
        df = self.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=120)
        if df.empty or len(df) < 50:
            return {"status": "error", "message": f"Insuficientes datos para {symbol}"}
            
        df_indicators = TechnicalIndicators.calculate_all(df)
        signals = TechnicalIndicators.get_latest_signal_summary(df_indicators)
        patterns = PatternDetector.identify_candlestick_patterns(df_indicators)
        levels = PatternDetector.calculate_support_resistance(df_indicators)
        
        # Scoring técnico (-1.0 a +1.0)
        score = 0.0
        
        # Tendencia
        if signals.get("trend") == "STRONG_BULLISH":
            score += 0.4
        elif signals.get("trend") == "BULLISH":
            score += 0.2
        elif signals.get("trend") == "STRONG_BEARISH":
            score -= 0.4
        elif signals.get("trend") == "BEARISH":
            score -= 0.2
            
        # MACD
        if signals.get("macd_crossover") == "BULLISH_CROSS":
            score += 0.3
        elif signals.get("macd_crossover") == "BEARISH_CROSS":
            score -= 0.3
        elif signals.get("macd_hist", 0) > 0:
            score += 0.1
        else:
            score -= 0.1
            
        # RSI
        rsi = signals.get("rsi", 50)
        if 40 <= rsi <= 60:
            score += 0.05 # Zona neutral/saludable
        elif rsi < 30:
            score += 0.2 # Posible rebote por sobreventa
        elif rsi > 70:
            score -= 0.2 # Posible agotamiento por sobrecompra
            
        # Patrones de velas
        for p in patterns:
            if p["bias"] == "BULLISH":
                score += 0.2 if p["strength"] == "HIGH" else 0.1
            elif p["bias"] == "BEARISH":
                score -= 0.2 if p["strength"] == "HIGH" else 0.1
                
        # Normalizar score entre -1.0 y 1.0
        normalized_score = max(-1.0, min(1.0, score))
        
        if normalized_score >= 0.35:
            bias = "BUY"
        elif normalized_score <= -0.35:
            bias = "SELL"
        else:
            bias = "HOLD / NEUTRAL"
            
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "price": signals.get("close"),
            "bias": bias,
            "technical_score": round(normalized_score, 2),
            "signals": signals,
            "patterns": patterns,
            "levels": levels,
            "status": "success"
        }
