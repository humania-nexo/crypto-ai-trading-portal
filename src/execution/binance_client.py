"""
Binance Live Execution, Complete Portfolio Valuator & Real-Time Sync.
Calculates exact account net worth across all crypto assets (SHIB, BTC, ETH, etc.)
even when locked in open orders (OCO, Limit).
"""

import ccxt
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BinanceLiveClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.is_connected = False
        self.client = None
        
        if api_key and api_secret and len(api_key) > 10:
            try:
                self.client = ccxt.binance({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot',
                        'adjustForTimeDifference': True
                    }
                })
                if self.testnet:
                    self.client.set_sandbox_mode(True)
                self.is_connected = True
            except Exception as e:
                logger.error(f"Error initializing Binance client: {e}")
                self.is_connected = False

    def get_complete_account_valuation(self) -> Dict[str, Any]:
        """
        Calcula el valor patrimonial total exacto de la cuenta:
        1. Saldo en USDT (libre y en órdenes).
        2. Todas las criptomonedas en posesión (SHIB, BTC, SOL, BNB, etc.),
           incluso si están bloqueadas en órdenes OCO o de venta.
        3. Convierte cada criptomoneda a su valor actual en dólares (USDT).
        """
        if not self.client:
            return {
                "status": "not_connected",
                "total_equity_usdt": 0.0,
                "cash_usdt": 0.0,
                "crypto_value_usdt": 0.0,
                "assets": [],
                "open_orders": []
            }
            
        try:
            balance_raw = self.client.fetch_balance()
            total_equity = 0.0
            cash_usdt = 0.0
            crypto_assets = []
            
            # 1. Obtener USDT directo
            usdt_info = balance_raw.get('USDT', {})
            free_usdt = float(usdt_info.get('free', 0.0))
            used_usdt = float(usdt_info.get('used', 0.0))
            cash_usdt = free_usdt + used_usdt
            total_equity += cash_usdt
            
            # 2. Iterar sobre todos los activos que tengan saldo > 0
            for currency, amounts in balance_raw.items():
                if currency in ['USDT', 'info', 'free', 'used', 'total', 'timestamp', 'datetime']:
                    continue
                if not isinstance(amounts, dict):
                    continue
                    
                total_coin = float(amounts.get('total', 0.0))
                free_coin = float(amounts.get('free', 0.0))
                used_coin = float(amounts.get('used', 0.0))
                
                if total_coin <= 0.00000001:
                    continue
                    
                # Obtener precio actual de la moneda en USDT
                symbol_pair = f"{currency}/USDT"
                unit_price = 0.0
                value_usdt = 0.0
                
                try:
                    ticker = self.client.fetch_ticker(symbol_pair)
                    unit_price = float(ticker.get('last', 0.0) or ticker.get('close', 0.0))
                    value_usdt = total_coin * unit_price
                except Exception:
                    # Si no cotiza directamente contra USDT o es polvo despreciable
                    pass
                    
                # Solo mostrar activos con valor relevante (> $0.05)
                if value_usdt >= 0.05:
                    total_equity += value_usdt
                    crypto_assets.append({
                        "asset": currency,
                        "symbol": symbol_pair,
                        "total_amount": total_coin,
                        "free_amount": free_coin,
                        "locked_in_orders": used_coin,
                        "unit_price_usdt": unit_price,
                        "value_usdt": round(value_usdt, 2)
                    })
                    
            # 3. Calcular porcentaje de cada activo
            for asset in crypto_assets:
                asset["percentage"] = round((asset["value_usdt"] / total_equity * 100) if total_equity > 0 else 0.0, 1)
                
            crypto_val = total_equity - cash_usdt
            
            # 4. Obtener órdenes abiertas activas
            open_orders = []
            try:
                raw_orders = self.client.fetch_open_orders()
                for o in raw_orders:
                    open_orders.append({
                        "id": o.get("id"),
                        "symbol": o.get("symbol"),
                        "type": o.get("type"),
                        "side": o.get("side").upper(),
                        "price": float(o.get("price", 0.0)),
                        "stop_price": float(o.get("stopPrice", 0.0) or 0.0),
                        "amount": float(o.get("amount", 0.0)),
                        "status": o.get("status"),
                        "datetime": o.get("datetime")
                    })
            except Exception as e:
                logger.warning(f"Could not fetch open orders: {e}")
                
            return {
                "status": "success",
                "total_equity_usdt": round(total_equity, 2),
                "cash_usdt": round(cash_usdt, 2),
                "crypto_value_usdt": round(crypto_val, 2),
                "assets": crypto_assets,
                "open_orders": open_orders,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching complete Binance valuation: {e}")
            return {
                "status": "error",
                "message": str(e),
                "total_equity_usdt": 0.0,
                "cash_usdt": 0.0,
                "crypto_value_usdt": 0.0,
                "assets": [],
                "open_orders": []
            }

    def execute_spot_buy_and_oco(
        self,
        symbol: str,
        usdt_amount: float,
        stop_loss_price: float,
        take_profit_price: float
    ) -> Dict[str, Any]:
        """Ejecuta compra a mercado y coloca orden OCO simultánea en Binance."""
        if not self.client:
            return {"status": "error", "message": "Binance Client no conectado"}
            
        try:
            market_buy = self.client.create_order(
                symbol=symbol,
                type='market',
                side='buy',
                amount=None,
                params={'quoteOrderQty': usdt_amount}
            )
            
            filled_qty = float(market_buy.get('filled', 0.0))
            avg_price = float(market_buy.get('average', 0.0)) or float(market_buy.get('price', 0.0))
            
            if filled_qty <= 0:
                return {"status": "error", "message": "No se pudo comprar en Binance"}
                
            formatted_qty = self.client.amount_to_precision(symbol, filled_qty)
            formatted_tp = self.client.price_to_precision(symbol, take_profit_price)
            formatted_sl_trigger = self.client.price_to_precision(symbol, stop_loss_price)
            formatted_sl_limit = self.client.price_to_precision(symbol, stop_loss_price * 0.998)
            
            raw_symbol = symbol.replace('/', '')
            oco_res = self.client.privatePostOrderOco({
                'symbol': raw_symbol,
                'side': 'SELL',
                'quantity': formatted_qty,
                'price': formatted_tp,
                'stopPrice': formatted_sl_trigger,
                'stopLimitPrice': formatted_sl_limit,
                'stopLimitTimeInForce': 'GTC'
            })
            
            return {
                "status": "success",
                "symbol": symbol,
                "entry_price": avg_price,
                "quantity": float(formatted_qty),
                "cost_usdt": usdt_amount,
                "buy_order_id": market_buy.get('id'),
                "oco_order_id": oco_res.get('orderListId'),
                "take_profit": take_profit_price,
                "stop_loss": stop_loss_price,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def sync_trades_from_binance(self, symbols: List[str] = None, limit: int = 15) -> List[Dict[str, Any]]:
        """Descarga compras y ventas recientes de Binance."""
        if not self.client:
            return []
            
        if symbols is None:
            symbols = ["SHIB/USDT", "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT", "AVAX/USDT", "PEPE/USDT"]
            
        all_my_trades = []
        for sym in symbols:
            try:
                my_trades = self.client.fetch_my_trades(symbol=sym, limit=limit)
                for tr in my_trades:
                    all_my_trades.append({
                        "id": tr.get("id"),
                        "symbol": tr.get("symbol"),
                        "side": tr.get("side").upper(),
                        "price": float(tr.get("price", 0.0)),
                        "amount": float(tr.get("amount", 0.0)),
                        "cost_usdt": float(tr.get("cost", 0.0)),
                        "fee_usdt": float(tr.get("fee", {}).get("cost", 0.0)) if tr.get("fee") else 0.0,
                        "datetime": tr.get("datetime") or datetime.utcnow().isoformat(),
                        "timestamp": tr.get("timestamp")
                    })
            except Exception:
                pass
                
        all_my_trades.sort(key=lambda x: x["timestamp"] or 0, reverse=True)
        return all_my_trades
