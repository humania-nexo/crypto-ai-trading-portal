"""
Advanced Chart Pattern Recognition & Classical Technical Analysis (Chartismo).
Detects:
1. Formaciones Chartistas Clásicas:
   - Doble Suelo (Double Bottom / Patrón W)
   - Hombro-Cabeza-Hombro Invertido (Inverse Head & Shoulders)
   - Banderín Alcista / Triángulo Ascendente (Bullish Pennant / Triangle)
   - Ruptura de Rango de Acumulación con Volumen (Breakout)
2. Patrones de Velas Japonesas (Hammer, Engulfing, Morning Star, Pinbars)
3. Zonas Históricas de Soporte y Resistencia Multi-Toque (Clusters de Pivotes)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

class PatternDetector:
    @staticmethod
    def find_pivots(df: pd.DataFrame, window: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Encuentra máximos y mínimos locales (Pivot Highs y Pivot Lows) en el histórico de precios."""
        highs = []
        lows = []
        
        for i in range(window, len(df) - window):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            
            # Es Pivot High si es mayor que los N periodos anteriores y posteriores
            if current_high == df['high'].iloc[i - window : i + window + 1].max():
                highs.append({
                    "index": i,
                    "price": float(current_high),
                    "datetime": df['datetime'].iloc[i] if 'datetime' in df.columns else i
                })
                
            # Es Pivot Low si es menor que los N periodos anteriores y posteriores
            if current_low == df['low'].iloc[i - window : i + window + 1].min():
                lows.append({
                    "index": i,
                    "price": float(current_low),
                    "datetime": df['datetime'].iloc[i] if 'datetime' in df.columns else i
                })
                
        return {"pivot_highs": highs, "pivot_lows": lows}

    @staticmethod
    def identify_chart_formations(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identifica formaciones chartistas estructurales completas (Doble Suelo, HCH Invertido, Banderines)."""
        if len(df) < 40:
            return []
            
        formations = []
        pivots = PatternDetector.find_pivots(df, window=4)
        p_lows = pivots["pivot_lows"]
        p_highs = pivots["pivot_highs"]
        current_price = float(df['close'].iloc[-1])
        
        # -------------------------------------------------------------
        # 1. DOBLE SUELO (DOUBLE BOTTOM / PATRÓN W) - Reversión Alcista
        # -------------------------------------------------------------
        if len(p_lows) >= 2:
            low1 = p_lows[-2]
            low2 = p_lows[-1]
            
            # Los dos mínimos deben estar en un rango de precio similar (+- 1.2% de tolerancia)
            price_diff_pct = abs(low1["price"] - low2["price"]) / low1["price"] * 100
            
            if price_diff_pct <= 1.2 and (low2["index"] - low1["index"]) >= 6:
                # Buscar el pico intermedio (Cuello / Neckline)
                neckline_candidates = [h for h in p_highs if low1["index"] < h["index"] < low2["index"]]
                if neckline_candidates:
                    neckline = max(neckline_candidates, key=lambda x: x["price"])
                    neckline_price = neckline["price"]
                    
                    if current_price >= low2["price"]:
                        status = "RUPTURA CONFIRMADA" if current_price >= neckline_price else "EN FORMACIÓN (Cerca del Suelo)"
                        formations.append({
                            "pattern": "DOBLE_SUELO_W",
                            "name": "Doble Suelo (Patrón W)",
                            "type": "REVERSIÓN ALCISTA",
                            "strength": "ALTA 🔥",
                            "status": status,
                            "neckline": round(neckline_price, 4),
                            "target_price": round(neckline_price + (neckline_price - low1["price"]), 4),
                            "description": f"Formación de doble suelo en ${low1['price']:,.2f} y ${low2['price']:,.2f}. El precio testeó dos veces el mismo nivel y rebotó."
                        })

        # -------------------------------------------------------------
        # 2. HOMBRO-CABEZA-HOMBRO INVERTIDO (iH&S) - Reversión Mayor
        # -------------------------------------------------------------
        if len(p_lows) >= 3:
            left_shoulder = p_lows[-3]
            head = p_lows[-2]
            right_shoulder = p_lows[-1]
            
            # La cabeza debe ser el punto más bajo (Head < Left Shoulder y Head < Right Shoulder)
            if head["price"] < left_shoulder["price"] and head["price"] < right_shoulder["price"]:
                shoulder_diff_pct = abs(left_shoulder["price"] - right_shoulder["price"]) / left_shoulder["price"] * 100
                if shoulder_diff_pct <= 2.0:
                    formations.append({
                        "pattern": "HCH_INVERTIDO",
                        "name": "Hombro-Cabeza-Hombro Invertido",
                        "type": "REVERSIÓN MAYOR ALCISTA",
                        "strength": "MUY ALTA 🔥🔥",
                        "target_price": round(current_price + (left_shoulder["price"] - head["price"]), 4),
                        "description": f"Patrón de cambio de tendencia: Hombro izq (${left_shoulder['price']:,.2f}), Cabeza (${head['price']:,.2f}) y Hombro der (${right_shoulder['price']:,.2f})."
                    })

        # -------------------------------------------------------------
        # 3. BANDERÍN / TRIÁNGULO ASCENDENTE (BULLISH PENNANT / TRIANGLE)
        # -------------------------------------------------------------
        if len(p_lows) >= 2 and len(p_highs) >= 2:
            recent_lows = p_lows[-2:]
            recent_highs = p_highs[-2:]
            
            # Mínimos cada vez más altos (Higher Lows)
            higher_lows = recent_lows[1]["price"] > recent_lows[0]["price"]
            
            # Máximos en resistencia horizontal o convergentes (Triángulo Ascendente)
            high_diff = abs(recent_highs[1]["price"] - recent_highs[0]["price"]) / recent_highs[0]["price"] * 100
            
            if higher_lows and high_diff <= 1.0:
                formations.append({
                    "pattern": "TRIANGULO_ASCENDENTE",
                    "name": "Triángulo Ascendente / Banderín",
                    "type": "CONTINUACIÓN ALCISTA",
                    "strength": "ALTA 🔥",
                    "resistance": round(recent_highs[1]["price"], 4),
                    "description": "Compradores presionando con mínimos cada vez más altos contra una resistencia fija. Presión alcista acumulada."
                })

        # -------------------------------------------------------------
        # 4. RUPTURA DE RANGO CON VOLUMEN (BREAKOUT)
        # -------------------------------------------------------------
        last_20 = df.tail(20)
        recent_max = last_20['high'].iloc[:-1].max()
        if current_price > recent_max:
            last_vol_ratio = df['volume_ratio'].iloc[-1] if 'volume_ratio' in df.columns else 1.0
            if last_vol_ratio >= 1.5:
                formations.append({
                    "pattern": "RUPTURA_RESISTENCIA_VOLUMEN",
                    "name": "Ruptura de Resistencia con Inyección de Volumen",
                    "type": "MOMENTUM & RUPTURA",
                    "strength": "ALTA 🔥",
                    "description": f"El precio acaba de superar el máximo de 20 periodos (${recent_max:,.2f}) con {last_vol_ratio:.1f}x más volumen del promedio."
                })

        return formations

    @staticmethod
    def identify_candlestick_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analiza las últimas velas para encontrar patrones de gatillo de entrada rápida."""
        if len(df) < 5:
            return []
            
        patterns = []
        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]
        
        body = abs(last['close'] - last['open'])
        upper_wick = last['high'] - max(last['close'], last['open'])
        lower_wick = min(last['close'], last['open']) - last['low']
        candle_range = last['high'] - last['low'] + 1e-10
        
        prev_body = abs(prev['close'] - prev['open'])
        
        is_bullish = last['close'] > last['open']
        is_prev_bearish = prev['close'] < prev['open']
        
        # 1. Bullish Engulfing (Envolvente alcista)
        if is_prev_bearish and is_bullish and last['open'] <= prev['close'] and last['close'] >= prev['open'] and body > prev_body * 1.1:
            patterns.append({
                "pattern": "BULLISH_ENGULFING",
                "bias": "BULLISH",
                "strength": "ALTA",
                "description": "Vela verde envolvente que absorbe completamente la presión vendedora previa."
            })
            
        # 2. Hammer (Martillo alcista)
        if lower_wick >= body * 2.0 and upper_wick <= body * 0.3:
            patterns.append({
                "pattern": "HAMMER",
                "bias": "BULLISH",
                "strength": "MEDIA",
                "description": "Martillo con mecha inferior larga: rechazo contundente a caer más bajo."
            })
            
        # 3. Morning Star (Estrella del Amanecer)
        if prev2['close'] < prev2['open'] and (abs(prev['close'] - prev['open']) < abs(prev2['close'] - prev2['open']) * 0.4) and is_bullish and last['close'] > (prev2['open'] + prev2['close'])/2:
            patterns.append({
                "pattern": "MORNING_STAR",
                "bias": "BULLISH",
                "strength": "ALTA",
                "description": "Patrón de 3 velas de giro en suelo: final de caída e inicio de rally."
            })
            
        return patterns

    @staticmethod
    def calculate_historical_supports_resistances(df: pd.DataFrame, tolerance_pct: float = 0.6) -> Dict[str, Any]:
        """
        Calcula zonas históricas de soportes y resistencias agrupando pivotes multi-toque
        (Zonas donde el precio ha rebotado 2 o más veces en el pasado).
        """
        if len(df) < 30:
            return {"supports": [], "resistances": []}
            
        pivots = PatternDetector.find_pivots(df, window=3)
        current_price = float(df['close'].iloc[-1])
        
        # Agrupar pivotes cercanos en clusters de liquidez
        all_points = [p["price"] for p in pivots["pivot_highs"] + pivots["pivot_lows"]]
        if not all_points:
            all_points = df['low'].tolist() + df['high'].tolist()
            
        clusters = []
        sorted_points = sorted(all_points)
        
        # Agrupamiento por cercanía
        curr_cluster = [sorted_points[0]]
        for pt in sorted_points[1:]:
            if (pt - curr_cluster[-1]) / curr_cluster[-1] * 100 <= tolerance_pct:
                curr_cluster.append(pt)
            else:
                if len(curr_cluster) >= 2: # Al menos 2 toques históricos
                    clusters.append({
                        "level": round(float(np.mean(curr_cluster)), 4),
                        "touches": len(curr_cluster)
                    })
                curr_cluster = [pt]
                
        if len(curr_cluster) >= 2:
            clusters.append({
                "level": round(float(np.mean(curr_cluster)), 4),
                "touches": len(curr_cluster)
            })
            
        # Separar en soportes (abajo del precio actual) y resistencias (arriba)
        supports = sorted([c for c in clusters if c["level"] < current_price], key=lambda x: x["level"], reverse=True)
        resistances = sorted([c for c in clusters if c["level"] > current_price], key=lambda x: x["level"])
        
        nearest_sup = supports[0]["level"] if supports else float(df['low'].min())
        nearest_res = resistances[0]["level"] if resistances else float(df['high'].max())
        
        return {
            "current_price": current_price,
            "nearest_support": nearest_sup,
            "nearest_resistance": nearest_res,
            "support_clusters": supports[:3],
            "resistance_clusters": resistances[:3]
        }
