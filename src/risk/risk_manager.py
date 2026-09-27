"""
Risk Management Engine.
Enforces strict capital preservation rules:
- Position sizing based on account balance & max risk % per trade.
- Dynamic Stop-Loss (ATR or Structural Support).
- Dynamic Take-Profit (Min Risk/Reward 1:2).
- Circuit Breaker: Daily max loss limit.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(
        self,
        max_risk_per_trade_pct: float = 1.0,  # Arriesgar máximo 1% del capital por operación
        max_daily_loss_pct: float = 3.0,       # Pérdida máxima diaria permitida (3%)
        min_risk_reward_ratio: float = 2.0     # Ratio Riesgo/Beneficio mínimo 1:2
    ):
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.min_risk_reward_ratio = min_risk_reward_ratio
        
        self.daily_starting_balance = 0.0
        self.current_daily_realized_pnl = 0.0

    def set_daily_baseline(self, current_balance: float):
        """Establece el balance inicial del día para el control de pérdidas acumuladas."""
        self.daily_starting_balance = current_balance
        self.current_daily_realized_pnl = 0.0

    def can_open_trade(self, current_balance: float) -> (bool, str):
        """Verifica si el Circuit Breaker permite nuevas operaciones."""
        if self.daily_starting_balance > 0:
            loss_pct = ((current_balance - self.daily_starting_balance) / self.daily_starting_balance) * 100
            if loss_pct <= -self.max_daily_loss_pct:
                return False, f"CIRCUIT BREAKER ACTIVO: Pérdida diaria de {loss_pct:.2f}% excede el límite de {self.max_daily_loss_pct}%."
        return True, "OK"

    def calculate_trade_parameters(
        self,
        symbol: str,
        entry_price: float,
        atr: float,
        nearest_support: Optional[float],
        account_balance: float
    ) -> Dict[str, Any]:
        """Calcula el Stop-Loss, Take-Profit y el tamaño de la posición respetando la gestión de riesgo."""
        
        # 1. Cálculo de distancia de Stop Loss (usamos el mayor entre 1.5 * ATR o soporte estructural con buffer)
        atr_sl_dist = atr * 1.5
        
        if nearest_support and nearest_support < entry_price:
            structural_sl_dist = (entry_price - nearest_support) + (atr * 0.5)
            # Usar la distancia estructural si es razonable (< 5% del precio)
            sl_distance = min(structural_sl_dist, atr_sl_dist)
        else:
            sl_distance = atr_sl_dist
            
        # Asegurar un SL mínimo del 0.5% y máximo del 3.5%
        min_sl_dist = entry_price * 0.005
        max_sl_dist = entry_price * 0.035
        sl_distance = max(min_sl_dist, min(max_sl_dist, sl_distance))
        
        stop_loss_price = entry_price - sl_distance
        
        # 2. Cálculo de Take-Profit (mínimo 1:2 R:R)
        tp_distance = sl_distance * self.min_risk_reward_ratio
        take_profit_price = entry_price + tp_distance
        
        # 3. Cálculo de Position Size (Monto a comprar en USDT)
        # Riesgo máximo en dólares para esta operación
        max_dollar_risk = account_balance * (self.max_risk_per_trade_pct / 100.0)
        
        # Porcentaje de pérdida si toca el Stop Loss
        loss_percentage = sl_distance / entry_price
        
        # Tamaño de posición ideal en USDT
        position_size_usdt = max_dollar_risk / loss_percentage
        
        # Límite de seguridad: nunca asignar más del 30% del balance total a un solo par en spot
        max_position_cap = account_balance * 0.30
        position_size_usdt = min(position_size_usdt, max_position_cap)
        
        # En Binance spot el mínimo por orden suele ser 5 a 10 USDT
        if position_size_usdt < 5.0 and account_balance >= 10.0:
            position_size_usdt = 10.0 # Ajuste mínimo Spot
            
        quantity = position_size_usdt / entry_price
        
        return {
            "symbol": symbol,
            "entry_price": round(entry_price, 4),
            "stop_loss": round(stop_loss_price, 4),
            "take_profit": round(take_profit_price, 4),
            "risk_reward_ratio": round(tp_distance / sl_distance, 2),
            "sl_percent": round((sl_distance / entry_price) * 100, 2),
            "tp_percent": round((tp_distance / entry_price) * 100, 2),
            "position_size_usdt": round(position_size_usdt, 2),
            "quantity": round(quantity, 6),
            "max_risk_usdt": round(position_size_usdt * (sl_distance / entry_price), 2)
        }
