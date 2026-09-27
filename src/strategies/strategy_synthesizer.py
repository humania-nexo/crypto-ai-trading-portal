"""
Strategy Synthesizer & Master Decision Agent.
Fuses:
1. Quantitative Technical Analysis (Trend + Momentum + Patterns)
2. Fundamental & News Sentiment (Fear & Greed + News Score)
3. Risk Manager Approval (SL/TP & Position Size)
"""

import logging
from typing import Dict, Any, Optional
from src.analysis.technical_agent import TechnicalAgent
from src.news.sentiment_agent import SentimentAgent
from src.risk.risk_manager import RiskManager
from src.execution.paper_broker import PaperBroker

logger = logging.getLogger(__name__)

class StrategySynthesizer:
    def __init__(
        self,
        tech_agent: TechnicalAgent,
        sentiment_agent: SentimentAgent,
        risk_manager: RiskManager,
        broker: PaperBroker
    ):
        self.tech_agent = tech_agent
        self.sentiment_agent = sentiment_agent
        self.risk_manager = risk_manager
        self.broker = broker

    def evaluate_market_and_execute(self, symbol: str = "BTC/USDT", timeframe: str = "15m") -> Dict[str, Any]:
        """Evalúa un par combinando todas las capas de inteligencia y ejecuta si hay confluencia."""
        
        # 1. Análisis Técnico
        tech_analysis = self.tech_agent.analyze_pair(symbol, timeframe)
        if tech_analysis.get("status") != "success":
            return {"status": "skipped", "reason": "Error en datos técnicos"}
            
        current_price = tech_analysis["price"]
        tech_score = tech_analysis["technical_score"] # -1.0 a +1.0
        
        # 2. Análisis de Sentimiento y Noticias
        sentiment_summary = self.sentiment_agent.get_market_sentiment_summary()
        sentiment_score = sentiment_summary["overall_score"] # -1.0 a +1.0
        
        # 3. Puntuación de Confluencia (70% Técnico + 30% Sentimiento)
        confluence_score = (tech_score * 0.70) + (sentiment_score * 0.30)
        
        # 4. Actualizar posiciones existentes con el precio actual
        closed_trades = self.broker.update_and_check_positions({symbol: current_price})
        
        # 5. Comprobar si podemos abrir nuevas operaciones (Riesgo / Circuit Breaker)
        portfolio = self.broker.get_portfolio_summary({symbol: current_price})
        can_trade, risk_msg = self.risk_manager.can_open_trade(portfolio["total_equity_usdt"])
        
        trade_decision = {
            "symbol": symbol,
            "current_price": current_price,
            "tech_score": tech_score,
            "sentiment_score": sentiment_score,
            "confluence_score": round(confluence_score, 2),
            "bias": tech_analysis["bias"],
            "news_sentiment": sentiment_summary["overall_sentiment"],
            "fear_and_greed": sentiment_summary["fear_and_greed"]["score"],
            "closed_trades_this_cycle": closed_trades,
            "action": "HOLD",
            "reason": ""
        }
        
        if not can_trade:
            trade_decision["reason"] = f"Bloqueado por Gestión de Riesgo: {risk_msg}"
            return trade_decision
            
        # Filtro de compra: Confluencia >= 0.30 y Sentimiento NO extremadamente bajista
        if confluence_score >= 0.30 and sentiment_score > -0.6:
            signals = tech_analysis["signals"]
            levels = tech_analysis["levels"]
            
            # Calcular parámetros de orden con el Agente de Riesgo
            trade_params = self.risk_manager.calculate_trade_parameters(
                symbol=symbol,
                entry_price=current_price,
                atr=signals["atr"],
                nearest_support=levels.get("nearest_support"),
                account_balance=portfolio["cash_balance_usdt"]
            )
            
            # Intentar ejecutar en el simulador
            exec_result = self.broker.open_buy_order(
                symbol=symbol,
                price=current_price,
                quantity=trade_params["quantity"],
                stop_loss=trade_params["stop_loss"],
                take_profit=trade_params["take_profit"],
                reason=f"Confluencia alcista ({confluence_score:.2f}) + {signals.get('trend')}"
            )
            
            if exec_result["status"] == "executed":
                trade_decision["action"] = "BUY_EXECUTED"
                trade_decision["trade_details"] = trade_params
                trade_decision["reason"] = f"Orden de compra ejecutada con SL @ ${trade_params['stop_loss']} y TP @ ${trade_params['take_profit']}."
            else:
                trade_decision["action"] = "BUY_ATTEMPTED_FAILED"
                trade_decision["reason"] = exec_result["message"]
        else:
            trade_decision["reason"] = "Puntuación de confluencia insuficiente para entrar al mercado."
            
        return trade_decision
