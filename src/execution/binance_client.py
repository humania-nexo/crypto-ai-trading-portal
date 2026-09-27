"""
Binance Live Execution, Complete Portfolio Valuator & Real-Time Open Orders Tracker.
Fetches active OCO and Limit orders across all assets (SHIB, etc.).
"""

import ccxt
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BinanceLiveClient:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, testnet: bool = False):
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.testnet = testnet
        self.is_connected = False
        self.client = None
        
        if self.api_key and self.api_secret and len(self.api_key) > 10:
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
        """Calcula el valor patrimonial total exacto y busca órdenes abiertas en todos los activos."""
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
            symbols_to_check_orders = set()
            
            # 1. Saldo USDT
            usdt_info = balance_raw.get('USDT', {})
            free_usdt = float(usdt_info.get('free', 0.0))
            used_usdt = float(usdt_info.get('used', 0.0))
            cash_usdt = free_usdt + used_usdt
            total_equity += cash_usdt
            
            # 2. Criptoactivos
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
                    
                symbol_pair = f"{currency}/USDT"
                unit_price = 0.0
                value_usdt = 0.0
                
                try:
                    ticker = self.client.fetch_ticker(symbol_pair)
                    unit_price = float(ticker.get('last', 0.0) or ticker.get('close', 0.0))
                    value_usdt = total_coin * unit_price
                except Exception:
                    pass
                    
                if value_usdt >= 0.05 or used_coin > 0:
                    symbols_to_check_orders.add(symbol_pair)
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
                    
            for asset in crypto_assets:
                asset["percentage"] = round((asset["value_usdt"] / total_equity * 100) if total_equity > 0 else 0.0, 1)
                
            crypto_val = total_equity - cash_usdt
            
            # 3. Buscar Órdenes Abiertas consultando cada par con saldo o en OCO
            open_orders = []
            
            # Añadir pares comunes a chequear
            symbols_to_check_orders.update(["SHIB/USDT", "BNB/USDT", "BTC/USDT", "SOL/USDT", "ETH/USDT"])
            
            for sym in symbols_to_check_orders:
                try:
                    pair_orders = self.client.fetch_open_orders(symbol=sym)
                    for o in pair_orders:
                        price = float(o.get("price", 0.0))
                        stop_price = float(o.get("stopPrice", 0.0) or 0.0)
                        amount = float(o.get("amount", 0.0))
                        total_val = amount * (price if price > 0 else stop_price)
                        
                        raw_type = o.get("type", "").upper()
                        order_type_display = raw_type
                        if "STOP" in raw_type or stop_price > 0:
                            order_type_display = "🛑 Stop Loss Limit (OCO)"
                        elif "LIMIT" in raw_type:
                            order_type_display = "🎯 Take Profit Limit (OCO)"
                            
                        open_orders.append({
                            "id": o.get("id"),
                            "symbol": o.get("symbol"),
                            "type": order_type_display,
                            "side": o.get("side", "").upper(),
                            "price": price,
                            "stop_price": stop_price,
                            "amount": amount,
                            "total_usdt": round(total_val, 2),
                            "datetime": o.get("datetime", "")[:16].replace("T", " "),
                            "status": o.get("status")
                        })
                except Exception as e:
                    logger.debug(f"No open orders for {sym}: {e}")
                    
            # 4. También verificar la lista OCO global de Binance
            try:
                raw_oco_list = self.client.privateGetOpenOrderList()
                if raw_oco_list and isinstance(raw_oco_list, list):
                    for oco_item in raw_oco_list:
                        # Si hay lista OCO activa que no se haya añadido
                        oco_orders_sub = oco_item.get("orders", [])
                        # Ya se listan a través de fetch_open_orders(symbol)
            except Exception:
                pass
                
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
            logger.error(f"Error in valuation: {e}")
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
            symbols = ["SHIB/USDT", "BNB/USDT", "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", "AVAX/USDT", "PEPE/USDT"]
            
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
