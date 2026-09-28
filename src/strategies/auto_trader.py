"""
Autonomous Trading Engine & Trailing Stop-Loss Manager.
Runs autonomous pilot trading cycles with:
1. Automated Entry on High Conviction setups (Score >= 0.35)
2. Trailing Stop-Loss (Moves to Break-Even at 50% target and trails peak price)
3. Dynamic Capital allocation limit per trade
4. Real-time Telegram alerting
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.analysis.market_scanner import MarketScanner
from src.execution.paper_broker import PaperBroker
from src.execution.binance_client import BinanceLiveClient
from src.notifications.telegram_bot import TelegramNotifier

logger = logging.getLogger(__name__)

class AutoTrader:
    def __init__(
        self,
        scanner: MarketScanner,
        broker: PaperBroker,
        binance_live: BinanceLiveClient,
        notifier: TelegramNotifier
    ):
        self.scanner = scanner
        self.broker = broker
        self.binance_live = binance_live
        self.notifier = notifier
        
        # Trailing stop state tracking
        self.peak_prices: Dict[str, float] = {}

    def update_trailing_stops(self, current_prices: Dict[str, float], is_live_trading: bool = False) -> List[str]:
        """
        Gestiona el Trailing Stop Dinámico:
        - Si el trade va ganando más del 50% del camino al Take Profit, mueve el Stop Loss al precio de entrada (Break-Even = Riesgo Cero).
        - Si sigue subiendo, protege las ganancias subiendo el Stop Loss detrás del precio.
        - En modo Real Binance: Cancela automáticamente la orden OCO vieja y coloca la nueva con el Stop Loss superior.
        """
        updated_symbols = []
        for symbol, pos in self.broker.open_positions.items():
            if symbol not in current_prices:
                continue
                
            current_p = current_prices[symbol]
            entry_p = pos["entry_price"]
            tp_p = pos["take_profit"]
            sl_p = pos["stop_loss"]
            
            # Registrar precio máximo alcanzado
            if symbol not in self.peak_prices:
                self.peak_prices[symbol] = entry_p
            if current_p > self.peak_prices[symbol]:
                self.peak_prices[symbol] = current_p
                
            target_gain = tp_p - entry_p
            current_gain = current_p - entry_p
            
            new_sl = None
            update_label = ""
            
            # 1. MOVER A BREAK-EVEN (Riesgo Cero) si alcanza el 50% del objetivo
            if current_gain >= (target_gain * 0.50) and sl_p < entry_p:
                new_sl = round(entry_p * 1.001, 8) # Entrada + comisión
                update_label = f"{symbol} (Protegido en Break-Even / Riesgo Cero)"
                
            # 2. TRAILING STOP: Si supera el 75% del objetivo, asegurar al menos 40% de ganancia
            elif current_gain >= (target_gain * 0.75) and sl_p < (entry_p + target_gain * 0.40):
                new_sl = round(entry_p + (target_gain * 0.40), 8)
                update_label = f"{symbol} (Trailing Stop Asegurando +40% de Ganancia)"
                
            if new_sl and new_sl > sl_p:
                pos["stop_loss"] = new_sl
                self.broker.save_state()
                updated_symbols.append(update_label)
                
                # Si estamos operando con dinero real en Binance, reemplazar la OCO en Binance
                if is_live_trading and self.binance_live.is_connected:
                    self.binance_live.update_live_oco_order(
                        symbol=symbol,
                        quantity=pos["quantity"],
                        new_stop_loss=new_sl,
                        take_profit=tp_p
                    )
                
        return updated_symbols

    def run_pilot_cycle(
        self,
        symbols: List[str],
        timeframe: str = "5m",
        max_active_positions: int = 3,
        capital_per_trade_usdt: float = 10.0,
        is_live_trading: bool = False
    ) -> Dict[str, Any]:
        """
        Ejecuta un ciclo completo del bot autónomo:
        1. Actualiza precios y verifica Trailing Stops y cierres OCO.
        2. Escanea el mercado en busca de oportunidades de Alta Convicción.
        3. Si hay cupo de capital, abre la mejor posición de forma automática.
        """
        log_messages = []
        
        # 1. Actualizar precios de posiciones abiertas
        current_prices = {}
        for sym in list(self.broker.open_positions.keys()):
            t_data = self.scanner.tech_agent.fetch_ohlcv(symbol=sym, timeframe=timeframe, limit=2)
            if not t_data.empty:
                current_prices[sym] = float(t_data.iloc[-1]["close"])
                
        # 2. Gestionar Trailing Stop
        trailing_updates = self.update_trailing_stops(current_prices, is_live_trading=is_live_trading)
        if trailing_updates:
            log_messages.extend([f"🛡️ Trailing Stop: {u}" for u in trailing_updates])
            
        # 3. Comprobar salidas automáticas (Take Profit o Stop Loss)
        closed_trades = self.broker.update_and_check_positions(current_prices)
        for cl_tr in closed_trades:
            log_messages.append(f"🏁 Trade Cerrado: {cl_tr['symbol']} ({cl_tr['exit_reason']}) -> PnL: ${cl_tr['pnl_usdt']:+,.2f} USDT")
            self.notifier.alert_trade_closed(cl_tr)
            if cl_tr['symbol'] in self.peak_prices:
                del self.peak_prices[cl_tr['symbol']]
                
        # 4. Comprobar si podemos abrir nuevas posiciones
        active_count = len(self.broker.open_positions)
        new_entries = []
        
        if active_count < max_active_positions:
            scan_res = self.scanner.scan_all_opportunities(
                symbols=symbols,
                timeframe=timeframe,
                min_score_threshold=0.35 # Solo ALTA CONVICCIÓN
            )
            
            top_opps = scan_res.get("top_opportunities", [])
            for opp in top_opps:
                if active_count >= max_active_positions:
                    break
                sym = opp["symbol"]
                if sym in self.broker.open_positions:
                    continue
                    
                # Abrir posición autónoma
                if is_live_trading and self.binance_live.is_connected:
                    exec_res = self.binance_live.execute_spot_buy_and_oco(
                        symbol=sym,
                        usdt_amount=capital_per_trade_usdt,
                        stop_loss_price=opp["stop_loss"],
                        take_profit_price=opp["take_profit"]
                    )
                    if exec_res["status"] == "success":
                        self.broker.open_buy_order(
                            symbol=sym,
                            price=exec_res["entry_price"],
                            quantity=exec_res["quantity"],
                            stop_loss=opp["stop_loss"],
                            take_profit=opp["take_profit"],
                            reason=f"Bot Real: {opp['setup_type']}"
                        )
                        new_entries.append(sym)
                        log_messages.append(f"🤖 COMPRA REAL AUTÓNOMA: {sym} por ${capital_per_trade_usdt:.2f} USDT con OCO.")
                        self.notifier.alert_new_opportunity(opp)
                        active_count += 1
                else:
                    # Modo Simulado Autónomo
                    qty = capital_per_trade_usdt / opp["price"]
                    res = self.broker.open_buy_order(
                        symbol=sym,
                        price=opp["price"],
                        quantity=qty,
                        stop_loss=opp["stop_loss"],
                        take_profit=opp["take_profit"],
                        reason=f"Bot Simulado: {opp['setup_type']}"
                    )
                    if res["status"] == "executed":
                        new_entries.append(sym)
                        log_messages.append(f"🤖 COMPRA SIMULADA AUTÓNOMA: {sym} a ${opp['price']:,.4f} USDT (SL: ${opp['stop_loss']:,.4f}, TP: ${opp['take_profit']:,.4f}).")
                        self.notifier.alert_new_opportunity(opp)
                        active_count += 1
                        
        return {
            "timestamp": datetime.utcnow().strftime("%H:%M:%S UTC"),
            "active_positions_count": len(self.broker.open_positions),
            "closed_trades_count": len(closed_trades),
            "new_entries": new_entries,
            "logs": log_messages
        }
