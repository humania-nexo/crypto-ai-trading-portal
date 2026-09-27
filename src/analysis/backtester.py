"""
Historical Backtesting Engine for Binance Scalping & Swing Strategies.
Simulates multi-indicator & pattern recognition strategies over historical OHLCV candles
with realistic Stop Loss, Take Profit, and Trailing Stop-to-Break-Even execution.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.analysis.indicators import TechnicalIndicators
from src.analysis.patterns import PatternDetector


class StrategyBacktester:
    def __init__(self, tech_agent):
        self.tech_agent = tech_agent

    def fetch_historical_dataset(
        self,
        symbol: str = "BTC/USDT",
        timeframe: str = "5m",
        total_candles: int = 500
    ) -> pd.DataFrame:
        """
        Descarga datos históricos de Binance para backtesting.
        """
        try:
            df = self.tech_agent.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=min(total_candles, 1000))
            if df.empty or len(df) < 50:
                return pd.DataFrame()
            return df
        except Exception as e:
            print(f"Error fetching backtest data for {symbol}: {e}")
            return pd.DataFrame()

    def run_backtest(
        self,
        symbol: str = "BTC/USDT",
        timeframe: str = "5m",
        total_candles: int = 500,
        initial_capital: float = 1000.0,
        capital_per_trade_usdt: float = 50.0,
        min_score_threshold: float = 0.30,
        enable_trailing_breakeven: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta la simulación histórica completa vela a vela.
        """
        df = self.fetch_historical_dataset(symbol, timeframe, total_candles)
        if df.empty or len(df) < 60:
            return {
                "error": f"Datos insuficientes para {symbol} ({len(df)} velas obtenidas, mínimo requerido: 60)."
            }

        # Pre-calcular indicadores para todo el dataset
        df = TechnicalIndicators.calculate_all(df)

        trades: List[Dict[str, Any]] = []
        in_trade = False
        current_trade = {}
        equity = initial_capital
        time_col = 'datetime' if 'datetime' in df.columns else 'timestamp'
        equity_curve = [{"timestamp": str(df.iloc[0][time_col]), "equity": equity, "price": float(df.iloc[0]["close"])}]

        # Empezamos desde la vela 30 para tener suficiente historial de EMAs y RSI
        for i in range(30, len(df)):
            current_row = df.iloc[i]
            prev_row = df.iloc[i - 1]
            ts = str(current_row[time_col])
            open_p = float(current_row["open"])
            high_p = float(current_row["high"])
            low_p = float(current_row["low"])
            close_p = float(current_row["close"])

            # 1. SI ESTAMOS EN UN TRADE, EVALUAR SALIDA
            if in_trade:
                entry_p = current_trade["entry_price"]
                sl_p = current_trade["stop_loss"]
                tp_p = current_trade["take_profit"]
                target_gain = tp_p - entry_p

                # Trailing stop a Break-Even si avanzó >= 50% hacia TP
                if enable_trailing_breakeven:
                    if (high_p - entry_p) >= (target_gain * 0.50) and sl_p < entry_p:
                        sl_p = entry_p * 1.0005 # Break-Even cubriendo comisión
                        current_trade["stop_loss"] = sl_p
                        current_trade["trailing_activated"] = True

                # Chequear si tocó Stop Loss o Take Profit en esta vela
                hit_sl = low_p <= sl_p
                hit_tp = high_p >= tp_p

                exit_triggered = False
                exit_price = None
                exit_reason = ""

                if hit_sl and hit_tp:
                    # En caso de alta volatilidad asumimos SL para ser conservadores
                    exit_price = sl_p
                    exit_reason = "Stop-Loss (Volatilidad)"
                    exit_triggered = True
                elif hit_sl:
                    exit_price = sl_p
                    exit_reason = "Stop-Loss"
                    exit_triggered = True
                elif hit_tp:
                    exit_price = tp_p
                    exit_reason = "Take-Profit"
                    exit_triggered = True
                elif (i - current_trade["entry_index"]) >= 36: # Timeout de 36 velas (ej. 3 horas en 5m)
                    exit_price = close_p
                    exit_reason = "Timeout Temporal"
                    exit_triggered = True

                if exit_triggered:
                    qty = current_trade["quantity"]
                    invested = current_trade["invested_usdt"]
                    exit_val = qty * exit_price
                    fee = (invested * 0.001) + (exit_val * 0.001) # 0.1% Binance Spot fee
                    pnl_usdt = (exit_val - invested) - fee
                    pnl_pct = ((exit_price - entry_p) / entry_p) * 100

                    equity += pnl_usdt
                    in_trade = False

                    trades.append({
                        "entry_time": current_trade["entry_time"],
                        "exit_time": ts,
                        "type": "BUY / LONG",
                        "entry_price": entry_p,
                        "exit_price": exit_price,
                        "invested_usdt": invested,
                        "pnl_usdt": round(pnl_usdt, 2),
                        "pnl_pct": round(pnl_pct, 2),
                        "result": "WIN" if pnl_usdt > 0 else "LOSS",
                        "exit_reason": exit_reason,
                        "duration_candles": i - current_trade["entry_index"],
                        "setup": current_trade["setup"]
                    })
                    equity_curve.append({"timestamp": ts, "equity": round(equity, 2), "price": close_p})
                    continue

            # 2. SI NO ESTAMOS EN TRADE, EVALUAR ENTRADA
            if not in_trade:
                sub_df = df.iloc[max(0, i - 60):i + 1]
                formations = PatternDetector.identify_chart_formations(sub_df)
                candlesticks = PatternDetector.identify_candlestick_patterns(sub_df)

                tech_score = 0.0
                reasons = []

                ema20 = float(current_row.get("ema_20", 0))
                ema50 = float(current_row.get("ema_50", 0))
                ema200 = float(current_row.get("ema_200", 0))
                rsi = float(current_row.get("rsi", 50))
                macd_hist = float(current_row.get("macd_hist", 0))
                atr = float(current_row.get("atr", close_p * 0.015))

                # Tendencia EMA
                if close_p > ema20 > ema50 > ema200:
                    tech_score += 0.35
                    reasons.append("Tendencia Alcista Fuerte (Precio > EMA20 > EMA50 > EMA200)")
                elif close_p > ema50 > ema200:
                    tech_score += 0.20
                    reasons.append("Estructura Alcista")

                # RSI
                if 42 <= rsi <= 60:
                    tech_score += 0.20
                    reasons.append(f"RSI Saludable ({rsi:.1f})")
                elif rsi < 35:
                    tech_score += 0.25
                    reasons.append(f"RSI Sobrevendido ({rsi:.1f})")

                # MACD
                if macd_hist > 0 and prev_row.get("macd_hist", 0) <= 0:
                    tech_score += 0.25
                    reasons.append("Cruce Alcista de MACD reciente")
                elif macd_hist > 0:
                    tech_score += 0.10

                # Formaciones y Velas
                for f in formations:
                    tech_score += 0.20
                    reasons.append(f"Figura: {f['name']}")
                for c in candlesticks:
                    tech_score += 0.15
                    reasons.append(f"Vela: {c['pattern']}")

                if tech_score >= min_score_threshold:
                    sl_dist = max(atr * 1.8, close_p * 0.008)
                    sl_price = round(close_p - sl_dist, 6)
                    tp_price = round(close_p + (sl_dist * 2.2), 6) # Ratio R:R 1:2.2

                    invest_amt = min(capital_per_trade_usdt, equity * 0.95)
                    if invest_amt >= 10.0:
                        qty = invest_amt / close_p
                        in_trade = True
                        current_trade = {
                            "entry_time": ts,
                            "entry_index": i,
                            "entry_price": close_p,
                            "quantity": qty,
                            "invested_usdt": invest_amt,
                            "stop_loss": sl_price,
                            "take_profit": tp_price,
                            "setup": reasons[0] if reasons else "Confluencia de Indicadores",
                            "trailing_activated": False
                        }

            if i % 10 == 0:
                equity_curve.append({"timestamp": ts, "equity": round(equity, 2), "price": close_p})

        # Resumen Estadístico
        total_trades = len(trades)
        winning_trades = [t for t in trades if t["pnl_usdt"] > 0]
        losing_trades = [t for t in trades if t["pnl_usdt"] <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0

        total_profit = sum(t["pnl_usdt"] for t in winning_trades)
        total_loss = abs(sum(t["pnl_usdt"] for t in losing_trades))
        profit_factor = (total_profit / total_loss) if total_loss > 0 else (total_profit if total_profit > 0 else 1.0)
        net_pnl_usdt = sum(t["pnl_usdt"] for t in trades)
        net_return_pct = ((equity - initial_capital) / initial_capital) * 100

        # Drawdown Máximo
        eq_df = pd.DataFrame(equity_curve)
        if not eq_df.empty:
            eq_df["peak"] = eq_df["equity"].cummax()
            eq_df["drawdown"] = (eq_df["equity"] - eq_df["peak"]) / eq_df["peak"] * 100
            max_drawdown_pct = abs(float(eq_df["drawdown"].min()))
        else:
            max_drawdown_pct = 0.0

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "total_candles_analyzed": len(df),
            "start_date": str(df.iloc[0][time_col])[:16],
            "end_date": str(df.iloc[-1][time_col])[:16],
            "initial_capital": initial_capital,
            "final_equity": round(equity, 2),
            "net_pnl_usdt": round(net_pnl_usdt, 2),
            "net_return_pct": round(net_return_pct, 2),
            "total_trades": total_trades,
            "win_trades": win_count,
            "loss_trades": loss_count,
            "win_rate_pct": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "avg_trade_pnl_usdt": round(net_pnl_usdt / total_trades, 2) if total_trades > 0 else 0.0,
            "trades": trades,
            "equity_curve": equity_curve
        }
