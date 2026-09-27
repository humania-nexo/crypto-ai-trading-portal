"""
Market Opportunity Scanner & AI Copilot (High-Throughput Concurrent Scanner).
Scans Top 30-50+ cryptocurrency pairs on Binance simultaneously using ThreadPool concurrency.
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.analysis.technical_agent import TechnicalAgent
from src.news.sentiment_agent import SentimentAgent
from src.risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)

# Listas curadas de pares líquidos en Binance Spot
TOP_30_LIQUID_PAIRS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
    "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "SUI/USDT", "NEAR/USDT",
    "LINK/USDT", "APT/USDT", "DOT/USDT", "PEPE/USDT", "SHIB/USDT",
    "WIF/USDT", "RENDER/USDT", "TAO/USDT", "FET/USDT", "INJ/USDT",
    "SEI/USDT", "TIA/USDT", "PENDLE/USDT", "AAVE/USDT", "UNI/USDT",
    "MATIC/USDT", "LTC/USDT", "ATOM/USDT", "OP/USDT", "ARB/USDT"
]

TOP_50_EXPANDED_PAIRS = TOP_30_LIQUID_PAIRS + [
    "FTM/USDT", "KAS/USDT", "BONK/USDT", "FLOKI/USDT", "GALA/USDT",
    "STX/USDT", "RUNE/USDT", "ALGO/USDT", "FIL/USDT", "HBAR/USDT",
    "ICP/USDT", "BCH/USDT", "ETC/USDT", "ENA/USDT", "WLD/USDT",
    "JUP/USDT", "PYTH/USDT", "ONDO/USDT", "ARKM/USDT", "NOT/USDT"
]

CATEGORIES = {
    "🔥 Top 30 Alta Liquidez (Recomendado)": TOP_30_LIQUID_PAIRS,
    "🌐 Top 50 Mercado Completo": TOP_50_EXPANDED_PAIRS,
    "🚀 Layer 1s & Layer 2s": [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "AVAX/USDT",
        "SUI/USDT", "NEAR/USDT", "APT/USDT", "SEI/USDT", "ARB/USDT", "OP/USDT"
    ],
    "🤖 AI & Big Data Tokens": [
        "NEAR/USDT", "RENDER/USDT", "TAO/USDT", "FET/USDT", "ARKM/USDT", "WLD/USDT"
    ],
    "⚡ Memecoins (Alta Volatilidad)": [
        "DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "WIF/USDT", "BONK/USDT", "FLOKI/USDT"
    ]
}

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
        self.categories = CATEGORIES

    def _analyze_single_symbol(
        self,
        sym: str,
        timeframe: str,
        sentiment_score: float,
        fng_info: Dict[str, Any],
        market_sentiment: Dict[str, Any],
        min_score_threshold: float
    ) -> Optional[Dict[str, Any]]:
        """Analiza un solo par de forma aislada para ser ejecutado en paralelo."""
        try:
            analysis = self.tech_agent.analyze_pair(symbol=sym, timeframe=timeframe)
            if analysis.get("status") != "success":
                return None
                
            price = analysis["price"]
            tech_score = analysis["technical_score"]
            signals = analysis["signals"]
            patterns = analysis["patterns"]
            levels = analysis["levels"]
            
            # Puntuación global de confluencia (75% Técnico + 25% Sentimiento)
            total_score = (tech_score * 0.75) + (sentiment_score * 0.25)
            
            # REGLA SPOT: Si la tendencia es fuertemente bajista y no hay sobreventa ni patrón de suelo, descartar
            has_bullish_reversal_pattern = any(p["bias"] == "BULLISH" for p in patterns)
            rsi = signals.get("rsi", 50)
            
            if signals.get("trend") in ["STRONG_BEARISH", "BEARISH"] and not (has_bullish_reversal_pattern or rsi <= 35):
                return None
            
            # Explicaciones claras para compras SPOT
            reasons_technical = []
            reasons_fundamental = []
            setup_type = "Sin patrón claro"
            
            # 1. Setup de continuación alcista
            if signals.get("trend") == "STRONG_BULLISH":
                reasons_technical.append("🟢 **Continuación de Tendencia**: Estructura fuertemente alcista (Precio > EMA 20 > EMA 50 > EMA 200).")
                setup_type = "Continuación de Tendencia Alcista (Impulso)"
            elif signals.get("trend") == "BULLISH":
                reasons_technical.append("🟢 **Tendencia Alcista Activa**: El precio se mantiene sólido sobre las medias rápidas.")
                setup_type = "Tendencia Alcista Saludable"
                
            # 2. Setup de reversión / rebote en soporte
            if rsi <= 35:
                reasons_technical.append(f"🎯 **Potencial Reversión Alcista por Sobreventa (RSI {rsi:.1f})**: Presión vendedora agotada en zona de descuento.")
                setup_type = "Reversión Alcista en Suelo / Rebote de Sobreventa"
            elif 45 <= rsi <= 62:
                reasons_technical.append(f"🟢 **RSI en Zona de Impulso Óptimo ({rsi:.1f})**: Espacio para subir sin riesgo de sobrecompra.")
            elif rsi >= 70:
                reasons_technical.append(f"⚠️ **RSI en Sobrecompra ({rsi:.1f})**: Cuidado con agotamiento a muy corto plazo.")
                
            # MACD
            if signals.get("macd_crossover") == "BULLISH_CROSS":
                reasons_technical.append("⚡ **Cruce Dorado de MACD**: Activación de impulso comprador fresco.")
                if setup_type == "Sin patrón claro":
                    setup_type = "Cruce de Momentum Alcista (MACD)"
            elif signals.get("macd_hist", 0) > 0:
                reasons_technical.append("🟢 **Momentum Positivo**: Compradores al mando en el histograma.")
                
            # Patrones de velas
            if patterns:
                for p in patterns:
                    if p["bias"] == "BULLISH":
                        reasons_technical.append(f"🕯️ **Giro Alcista (Vela)**: {p['pattern']} ({p['description']})")
                        if setup_type == "Sin patrón claro":
                            setup_type = f"Vela Alcista ({p['pattern']})"
                            
            # Formaciones Chartistas Estructurales (Doble Suelo, HCH Invertido, Banderines)
            chart_forms = analysis.get("chart_formations", [])
            if chart_forms:
                for f in chart_forms:
                    reasons_technical.append(f"📐 **Figura Chartista Detectada**: **{f['name']}** - {f['description']}")
                    setup_type = f"Figura Chartista: {f['name']}"
                    
            # Soportes y Resistencias Históricos Multi-Toque
            sup_clusters = levels.get("support_clusters", [])
            if sup_clusters:
                best_sup = sup_clusters[0]
                reasons_technical.append(f"🧱 **Soporte Histórico Fuerte**: Nivel en ${best_sup['level']:,.2f} con **{best_sup['touches']} toques/rebotes históricos** confirmados.")
                    
            # Volumen
            if signals.get("volume_spike"):
                reasons_technical.append("🔥 **Inyección de Volumen**: Fuerte entrada de capital en velas recientes.")
                
            # Razones Macro
            reasons_fundamental.append(f"📊 **Sentimiento Global**: Fear & Greed en {fng_info['score']}/100 ({fng_info['sentiment']}).")
            if market_sentiment["overall_sentiment"] == "BULLISH":
                reasons_fundamental.append("📰 **Viento a Favor en Noticias**: Flujo informativo positivo para el mercado cripto.")
            elif market_sentiment["overall_sentiment"] == "BEARISH":
                reasons_fundamental.append("⚠️ **Ambiente Cauto en Medios**: Operar con Stop-Loss ajustado por volatilidad.")
                
            # Calcular propuesta de Stop Loss y Take Profit
            trade_params = self.risk_manager.calculate_trade_parameters(
                symbol=sym,
                entry_price=price,
                atr=signals.get("atr", price * 0.01),
                nearest_support=levels.get("nearest_support"),
                account_balance=100.0
            )
            
            # Calificación
            if total_score >= 0.35:
                conviction = "ALTA CONVICCIÓN 🔥"
                recommendation = "COMPRA EN SPOT (ALTA PROBABILIDAD)"
            elif total_score >= min_score_threshold:
                conviction = "MODERADA ⚡"
                recommendation = "COMPRA EN SPOT (MODERADA)"
            else:
                conviction = "NEUTRAL / BAJA ⏳"
                recommendation = "MANTENERSE EN LIQUIDEZ (USDT)"
                
            return {
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
        except Exception as e:
            logger.error(f"Error analyzing {sym}: {e}")
            return None

    def scan_all_opportunities(
        self,
        symbols: List[str] = None,
        timeframe: str = "5m",
        min_score_threshold: float = 0.15,
        max_workers: int = 12
    ) -> Dict[str, Any]:
        """Escanea todos los pares concurrentemente a alta velocidad."""
        if symbols is None:
            symbols = TOP_30_LIQUID_PAIRS
            
        market_sentiment = self.sentiment_agent.get_market_sentiment_summary()
        sentiment_score = market_sentiment["overall_score"]
        fng_info = market_sentiment["fear_and_greed"]
        
        opportunities = []
        
        # Ejecución paralela multihilo para escanear decenas de pares en ~2 segundos
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    self._analyze_single_symbol,
                    sym,
                    timeframe,
                    sentiment_score,
                    fng_info,
                    market_sentiment,
                    min_score_threshold
                )
                for sym in symbols
            ]
            
            for future in as_completed(futures):
                res = future.result()
                if res and res["score"] >= min_score_threshold:
                    opportunities.append(res)
                    
        # Ordenar de mayor a menor puntuación
        opportunities.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "scanned_count": len(symbols),
            "timeframe": timeframe,
            "fear_and_greed": fng_info,
            "overall_news_sentiment": market_sentiment["overall_sentiment"],
            "opportunities_found": len(opportunities),
            "top_opportunities": opportunities
        }
