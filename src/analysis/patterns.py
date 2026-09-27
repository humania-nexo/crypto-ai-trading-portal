"""
Pattern Recognition & Price Action Module.
Identifies:
- Key Support and Resistance zones (Dynamic Pivots)
- Candlestick patterns (Engulfing, Hammer, Shooting Star, Morning/Evening Star, Doji)
- Range Breakouts and Rejections
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any

class PatternDetector:
    @staticmethod
    def identify_candlestick_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analiza las últimas velas para encontrar patrones de confirmación de acción de precio."""
        if len(df) < 5:
            return []
            
        patterns = []
        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]
        
        # Geometría de la vela actual
        body = abs(last['close'] - last['open'])
        upper_wick = last['high'] - max(last['close'], last['open'])
        lower_wick = min(last['close'], last['open']) - last['low']
        candle_range = last['high'] - last['low'] + 1e-10
        
        # Geometría de la vela previa
        prev_body = abs(prev['close'] - prev['open'])
        
        is_bullish = last['close'] > last['open']
        is_prev_bearish = prev['close'] < prev['open']
        is_prev_bullish = prev['close'] > prev['open']
        
        # 1. Bullish Engulfing (Vela envolvente alcista)
        if is_prev_bearish and is_bullish and last['open'] <= prev['close'] and last['close'] >= prev['open'] and body > prev_body * 1.1:
            patterns.append({
                "pattern": "BULLISH_ENGULFING",
                "bias": "BULLISH",
                "strength": "HIGH",
                "description": "Vela verde que envuelve completamente el cuerpo de la vela roja previa."
            })
            
        # 2. Bearish Engulfing (Vela envolvente bajista)
        if is_prev_bullish and not is_bullish and last['open'] >= prev['close'] and last['close'] <= prev['open'] and body > prev_body * 1.1:
            patterns.append({
                "pattern": "BEARISH_ENGULFING",
                "bias": "BEARISH",
                "strength": "HIGH",
                "description": "Vela roja que envuelve completamente el cuerpo de la vela verde previa."
            })
            
        # 3. Hammer (Martillo alcista en soporte / fondo)
        if lower_wick >= body * 2.0 and upper_wick <= body * 0.3:
            patterns.append({
                "pattern": "HAMMER",
                "bias": "BULLISH",
                "strength": "MEDIUM",
                "description": "Rechazo fuerte de precios bajos (mecha inferior larga)."
            })
            
        # 4. Shooting Star / Inverted Hammer (Estrella fugaz)
        if upper_wick >= body * 2.0 and lower_wick <= body * 0.3:
            patterns.append({
                "pattern": "SHOOTING_STAR",
                "bias": "BEARISH",
                "strength": "MEDIUM",
                "description": "Rechazo fuerte de precios altos (mecha superior larga)."
            })
            
        # 5. Doji (Indecisión del mercado)
        if body / candle_range <= 0.1:
            patterns.append({
                "pattern": "DOJI",
                "bias": "NEUTRAL",
                "strength": "LOW",
                "description": "Apertura y cierre casi iguales, indicando indecisión."
            })
            
        # 6. Morning Star (Estrella de la mañana - 3 velas alcista)
        if prev2['close'] < prev2['open'] and (abs(prev['close'] - prev['open']) < abs(prev2['close'] - prev2['open']) * 0.4) and is_bullish and last['close'] > (prev2['open'] + prev2['close'])/2:
            patterns.append({
                "pattern": "MORNING_STAR",
                "bias": "BULLISH",
                "strength": "HIGH",
                "description": "Patrón de giro alcista de 3 velas (Fuerte impulso de reversión)."
            })
            
        return patterns

    @staticmethod
    def calculate_support_resistance(df: pd.DataFrame, window: int = 20) -> Dict[str, Any]:
        """Calcula niveles clave de soporte y resistencia basados en pivotes y extremos recientes."""
        if len(df) < window:
            return {"supports": [], "resistances": []}
            
        recent_highs = df['high'].rolling(window=window, center=False).max()
        recent_lows = df['low'].rolling(window=window, center=False).min()
        
        current_price = df.iloc[-1]['close']
        
        # Encontrar resistencias por encima del precio actual
        highs = sorted(list(set(df['high'].tail(50).nlargest(5).round(2).tolist())))
        resistances = [p for p in highs if p > current_price]
        
        # Encontrar soportes por debajo del precio actual
        lows = sorted(list(set(df['low'].tail(50).nsmallest(5).round(2).tolist())))
        supports = [p for p in lows if p < current_price]
        
        nearest_resistance = resistances[0] if resistances else float(df['high'].max())
        nearest_support = supports[-1] if supports else float(df['low'].min())
        
        return {
            "current_price": current_price,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "all_supports": supports,
            "all_resistances": resistances
        }
