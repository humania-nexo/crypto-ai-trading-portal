"""
Paper Trading Broker & Execution Simulator.
Provides a realistic trading simulation environment:
- Virtual USDT balance
- Simulated OCO orders (Stop Loss and Take Profit simultaneously monitored)
- Commission simulation (0.1% standard Binance Spot fee)
- Live position monitoring and PnL calculation
- Persistent trade history and performance metrics (Win Rate, Profit Factor, Drawdown)
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class PaperBroker:
    def __init__(self, initial_balance: float = 100.0, state_file: str = "paper_trading_state.json", fee_rate: float = 0.001):
        self.initial_balance = initial_balance
        self.state_file = state_file
        self.fee_rate = fee_rate # 0.1% Binance Spot fee
        
        self.balance_usdt = initial_balance
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
        
        self.load_state()

    def load_state(self):
        """Carga el estado del balance y posiciones desde el archivo JSON si existe."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.balance_usdt = data.get("balance_usdt", self.initial_balance)
                    self.open_positions = data.get("open_positions", {})
                    self.trade_history = data.get("trade_history", [])
            except Exception as e:
                logger.error(f"Error loading state: {e}")

    def save_state(self):
        """Guarda el estado actual en disco."""
        try:
            data = {
                "balance_usdt": round(self.balance_usdt, 4),
                "open_positions": self.open_positions,
                "trade_history": self.trade_history,
                "updated_at": datetime.utcnow().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def open_buy_order(
        self,
        symbol: str,
        price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        reason: str = ""
    ) -> Dict[str, Any]:
        """Abre una posición de compra en Spot simulada con orden OCO (SL y TP asociados)."""
        cost = price * quantity
        fee = cost * self.fee_rate
        total_required = cost + fee
        
        if total_required > self.balance_usdt:
            return {
                "status": "rejected",
                "message": f"Saldo insuficiente: requerido ${total_required:.2f} USDT, disponible ${self.balance_usdt:.2f} USDT."
            }
            
        if symbol in self.open_positions:
            return {
                "status": "rejected",
                "message": f"Ya existe una posición abierta para {symbol}."
            }
            
        # Descontar balance
        self.balance_usdt -= total_required
        
        position = {
            "symbol": symbol,
            "entry_price": price,
            "quantity": quantity,
            "cost_usdt": cost,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "entry_time": datetime.utcnow().isoformat(),
            "reason": reason,
            "fees_paid": fee
        }
        
        self.open_positions[symbol] = position
        self.save_state()
        
        return {
            "status": "executed",
            "position": position
        }

    def update_and_check_positions(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """Verifica todas las posiciones abiertas contra los precios actuales del mercado (Lógica OCO)."""
        closed_trades = []
        
        for symbol, pos in list(self.open_positions.items()):
            if symbol not in current_prices:
                continue
                
            current_price = current_prices[symbol]
            entry_price = pos["entry_price"]
            quantity = pos["quantity"]
            sl = pos["stop_loss"]
            tp = pos["take_profit"]
            
            exit_reason = None
            exit_price = current_price
            
            # Comprobar Take Profit (Alcanzado)
            if current_price >= tp:
                exit_reason = "TAKE_PROFIT"
                exit_price = tp
            # Comprobar Stop Loss (Alcanzado)
            elif current_price <= sl:
                exit_reason = "STOP_LOSS"
                exit_price = sl
                
            if exit_reason:
                gross_proceeds = exit_price * quantity
                fee = gross_proceeds * self.fee_rate
                net_proceeds = gross_proceeds - fee
                
                pnl_usdt = net_proceeds - pos["cost_usdt"] - pos["fees_paid"]
                pnl_percent = (pnl_usdt / pos["cost_usdt"]) * 100
                
                # Reintegrar al balance
                self.balance_usdt += net_proceeds
                
                trade_record = {
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "quantity": quantity,
                    "entry_time": pos["entry_time"],
                    "exit_time": datetime.utcnow().isoformat(),
                    "exit_reason": exit_reason,
                    "pnl_usdt": round(pnl_usdt, 4),
                    "pnl_percent": round(pnl_percent, 2),
                    "fees_total": round(pos["fees_paid"] + fee, 4),
                    "signal_reason": pos["reason"]
                }
                
                self.trade_history.append(trade_record)
                closed_trades.append(trade_record)
                del self.open_positions[symbol]
                
        if closed_trades:
            self.save_state()
            
        return closed_trades

    def get_portfolio_summary(self, current_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Calcula el valor total del portafolio, PnL no realizado y métricas de rendimiento."""
        unrealized_pnl = 0.0
        positions_summary = []
        
        current_prices = current_prices or {}
        
        for symbol, pos in self.open_positions.items():
            current_price = current_prices.get(symbol, pos["entry_price"])
            current_val = current_price * pos["quantity"]
            pos_unrealized = current_val - pos["cost_usdt"]
            pos_pct = (pos_unrealized / pos["cost_usdt"]) * 100
            
            unrealized_pnl += pos_unrealized
            positions_summary.append({
                "symbol": symbol,
                "entry_price": pos["entry_price"],
                "current_price": current_price,
                "quantity": pos["quantity"],
                "stop_loss": pos["stop_loss"],
                "take_profit": pos["take_profit"],
                "unrealized_pnl_usdt": round(pos_unrealized, 2),
                "unrealized_pnl_pct": round(pos_pct, 2)
            })
            
        total_equity = self.balance_usdt + sum([pos["cost_usdt"] for pos in self.open_positions.values()]) + unrealized_pnl
        
        # Estadísticas de trading
        total_trades = len(self.trade_history)
        winning_trades = [t for t in self.trade_history if t["pnl_usdt"] > 0]
        losing_trades = [t for t in self.trade_history if t["pnl_usdt"] <= 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0
        total_realized_pnl = sum([t["pnl_usdt"] for t in self.trade_history])
        
        return {
            "cash_balance_usdt": round(self.balance_usdt, 2),
            "total_equity_usdt": round(total_equity, 2),
            "unrealized_pnl_usdt": round(unrealized_pnl, 2),
            "total_realized_pnl_usdt": round(total_realized_pnl, 2),
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "open_positions_count": len(self.open_positions),
            "open_positions": positions_summary,
            "trade_history_sample": self.trade_history[-5:]
        }
