"""
Market Opportunity Scanner & AI Copilot.
Scans top cryptocurrency pairs on Binance, evaluates technical patterns, news sentiment,
and risk parameters to generate high-conviction trade setups with plain-language rationales.
"""

import logging
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime

from src.analysis.technical_agent import TechnicalAgent
from src.news.sentiment_agent import SentimentAgent
from src.risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class MarketScanner:
    def __init__(
        self,
        tech_agent: TechnicalAgent,
        sentiment_agent: SentimentAgent,
        risk_manager: RiskManager
    ):
        self.tech_agent = tech_agent
        self.sentiment_agent = sentiment_agent
        self.risk_manager = risk_manager
        
        # Lista de las principales criptomonedas líquidas en Binance Spot
        self.default_watchlist = [
            "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "LINK/USDT", "NEAR/USDT",
            "SUI/USDT", "DOT/USDT"
        ]

    def scan_all_opportunities(
        self,
        symbols: List[str] = None,
        timeframe: str = "15m",
        min_score_threshold: float = 0.20
    ) -> Dict[str, Any]:
        """
        Escanea todos los pares seleccionados y devuelve un ranking con las mejores
        oportunidades de entrada explicadas en lenguaje claro para el usuario.
        """
        if symbols is None:
            symbols = self.default_watchlist
            
        # 1. Obtener el contexto de noticias y sentimiento global
        market_sentiment = self.sentiment_agent.get_market_sentiment_summary()
        sentiment_score = market_sentiment["overall_score"]
        fng_info = market_sentiment["fear_and_greed"]
        
        opportunities = []
        neutral_or_no_setup = []
        
        for sym in symbols:
            try:
                analysis = self.tech_agent.analyze_pair(symbol=sym, timeframe=timeframe)
                if analysis.get("status") != "success":
                    continue
                    
                price = analysis["price"]
                tech_score = analysis["technical_score"]
                signals = analysis["signals"]
                patterns = analysis["patterns"]
                levels = analysis["levels"]
                
                # Puntuación global de confluencia (75% Técnico + 25% Sentimiento)
                total_score = (tech_score * 0.75) + (sentiment_score * 0.25)
                
                # Construir explicaciones claras y humanas
                reasons_technical = []
                reasons_fundamental = []
                setup_type = "Sin patrón claro"
                
                # Análisis de tendencia
                if signals.get("trend") == "STRONG_BULLISH":
                    reasons_technical.append("🟢 **Estructura Fuertemente Alcista**: Precio por encima de las 3 EMAs clave (20, 50 y 200).")
                elif signals.get("trend") == "BULLISH":
                    reasons_technical.append("🟢 **Tendencia Alcista Activa**: El precio se mantiene sobre las medias rápidas.")
                elif signals.get("trend") == "STRONG_BEARISH":
                    reasons_technical.append("🔴 **Tendencia Bajista**: El precio está por debajo de todas las medias.")
                    
                # RSI
                rsi = signals.get("rsi", 50)
                if rsi <= 35:
                    reasons_technical.append(f"🟢 **Sobreventa Favorable (RSI {rsi:.1f})**: Indica que la presión vendedora se está agotando (posible rebote).")
                    setup_type = "Rebote en Zona de Sobreventa"
                elif 45 <= rsi <= 60:
                    reasons_technical.append(f"🟢 **RSI en Zona de Impulso Saludable ({rsi:.1f})**: Hay espacio para subir sin estar sobrecomprado.")
                elif rsi >= 70:
                    reasons_technical.append(f"⚠️ **Precaución por Sobrecompra (RSI {rsi:.1f})**: El precio ha subido mucho a corto plazo.")
                    
                # MACD
                if signals.get("macd_crossover") == "BULLISH_CROSS":
                    reasons_technical.append("🟢 **Cruce Dorado de MACD**: Señal cuantitativa de inicio de impulso comprador.")
                    setup_type = "Cruce de Momentum Alcista (MACD)"
                elif signals.get("macd_hist", 0) > 0:
                    reasons_technical.append("🟢 **Momentum Positivo**: Histograma de MACD en terreno positivo.")
                    
                # Patrones de velas
                if patterns:
                    for p in patterns:
                        reasons_technical.append(f"🕯️ **Patrón de Vela Detectado**: {p['pattern']} ({p['description']})")
                        setup_type = f"Patrón de Vela ({p['pattern']})"
                        
                # Volumen
                if signals.get("volume_spike"):
                    reasons_technical.append("⚡ **Pico de Volumen Anómalo**: Fuerte participación de capital en las últimas velas.")
                    
                # Razones Fundamentales / Macro
                reasons_fundamental.append(f"📊 **Sentimiento Global**: Fear & Greed en {fng_info['score']}/100 ({fng_info['sentiment']}).")
                if market_sentiment["overall_sentiment"] == "BULLISH":
                    reasons_fundamental.append("📰 **Flujo de Noticias Positivo**: Predominan titulares favorables para el mercado cripto.")
                elif market_sentiment["overall_sentiment"] == "BEARISH":
                    reasons_fundamental.append("⚠️ **Noticias Cautas**: Hay noticias negativas recientes en los medios.")
                    
                # Calcular propuesta de Stop Loss y Take Profit
                trade_params = self.risk_manager.calculate_trade_parameters(
                    symbol=sym,
                    entry_price=price,
                    atr=signals.get("atr", price * 0.01),
                    nearest_support=levels.get("nearest_support"),
                    account_balance=100.0 # Proyección base
                )
                
                # Calificación de Calidad de la Oportunidad (Alta, Media, Baja)
                if total_score >= 0.40:
                    conviction = "ALTA CONVICCIÓN 🔥"
                    recommendation = "OPORTUNIDAD DE COMPRA CLARA"
                elif total_score >= min_score_threshold:
                    conviction = "MODERADA ⚡"
                    recommendation = "OPORTUNIDAD DE COMPRA MODERADA"
                else:
                    conviction = "NEUTRAL / BAJA ⏳"
                    recommendation = "MANTENERSE AL MARGEN (HOLD)"
                    
                opportunity_card = {
                    "symbol": sym,
                    "price": price,
                    "score": round(total_score, 2),
                    "conviction": conviction,
                    "recommendation": recommendation,
                    "setup_type": setup_type,
                    "technical_reasons": reasons_technical,
                    "fundamental_reasons": reasons_fundamental,
                    "entry_price": trade_params["entry_price"],
                    "stop_loss": trade_params["stop_loss"],
                    "take_profit": trade_params["take_profit"],
                    "sl_percent": trade_params["sl_percent"],
                    "tp_percent": trade_params["tp_percent"],
                    "risk_reward_ratio": trade_params["risk_reward_ratio"],
                    "timeframe": timeframe
                }
                
                if total_score >= min_score_threshold:
                    opportunities.append(opportunity_card)
                else:
                    neutral_or_no_setup.append(opportunity_card)
                    
            except Exception as e:
                logger.error(f"Error scanning {sym}: {e}")
                
        # Ordenar oportunidades de mayor a menor puntuación
        opportunities.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "timeframe": timeframe,
            "fear_and_greed": fng_info,
            "overall_news_sentiment": market_sentiment["overall_sentiment"],
            "opportunities_found": len(opportunities),
            "top_opportunities": opportunities,
            "other_scanned": neutral_or_no_setup
        }
