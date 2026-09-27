"""
Binance Live Execution & Two-Way Account Synchronizer.
Provides:
1. Real-time balance retrieval (USDT & Crypto assets)
2. Automated Spot Market Buy + OCO Sell placement
3. Two-way trade sync (Detects trades placed from Phone App or Web)
4. Active OCO open order monitoring
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

    def test_connection(self) -> Dict[str, Any]:
        """Prueba si las claves API son válidas y tienen permisos correctos."""
        if not self.client:
            return {"status": "error", "message": "Claves API no configuradas"}
        try:
            balance = self.client.fetch_balance()
            free_usdt = float(balance.get('USDT', {}).get('free', 0.0))
            total_usdt = float(balance.get('USDT', {}).get('total', 0.0))
            return {
                "status": "success",
                "free_usdt": free_usdt,
                "total_usdt": total_usdt,
                "balances": {k: v['total'] for k, v in balance.items() if isinstance(v, dict) and v.get('total', 0) > 0}
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_real_usdt_balance(self) -> float:
        """Obtiene el saldo libre en USDT directamente de Binance."""
        if not self.client:
            return 0.0
        try:
            balance = self.client.fetch_balance()
            return float(balance.get('USDT', {}).get('free', 0.0))
        except Exception as e:
            logger.error(f"Error fetching Binance balance: {e}")
            return 0.0

    def execute_spot_buy_and_oco(
        self,
        symbol: str,
        usdt_amount: float,
        stop_loss_price: float,
        take_profit_price: float
    ) -> Dict[str, Any]:
        """
        1. Compra a precio de mercado el monto en USDT.
        2. Inmediatamente coloca una orden OCO de venta con SL y TP en Binance Spot.
        """
        if not self.client:
            return {"status": "error", "message": "Binance Client no conectado"}
            
        try:
            # 1. Ejecutar compra a mercado
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
                return {"status": "error", "message": "No se pudo comprar la cantidad solicitada en Binance"}
                
            # 2. Ajustar precisión de cantidad y precios para Binance
            formatted_qty = self.client.amount_to_precision(symbol, filled_qty)
            formatted_tp = self.client.price_to_precision(symbol, take_profit_price)
            formatted_sl_trigger = self.client.price_to_precision(symbol, stop_loss_price)
            # SL Limit ligeramente inferior para asegurar ejecución
            formatted_sl_limit = self.client.price_to_precision(symbol, stop_loss_price * 0.998)
            
            # 3. Enviar orden OCO
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
            logger.error(f"Error executing Spot Buy + OCO on Binance: {e}")
            return {"status": "error", "message": str(e)}

    def sync_trades_from_binance(self, symbols: List[str] = None, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Descarga el historial de compras y ventas recientes en Binance Spot,
        detectando incluso operaciones hechas desde el móvil o la web oficial.
        """
        if not self.client:
            return []
            
        if symbols is None:
            symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "PEPE/USDT", "SHIB/USDT"]
            
        all_my_trades = []
        for sym in symbols:
            try:
                my_trades = self.client.fetch_my_trades(symbol=sym, limit=limit)
                for tr in my_trades:
                    all_my_trades.append({
                        "id": tr.get("id"),
                        "symbol": tr.get("symbol"),
                        "side": tr.get("side").upper(), # BUY or SELL
                        "price": float(tr.get("price", 0.0)),
                        "amount": float(tr.get("amount", 0.0)),
                        "cost_usdt": float(tr.get("cost", 0.0)),
                        "fee_usdt": float(tr.get("fee", {}).get("cost", 0.0)) if tr.get("fee") else 0.0,
                        "datetime": tr.get("datetime") or datetime.utcnow().isoformat(),
                        "timestamp": tr.get("timestamp")
                    })
            except Exception as e:
                logger.warning(f"No trades or error for {sym}: {e}")
                
        # Ordenar por fecha más reciente primero
        all_my_trades.sort(key=lambda x: x["timestamp"] or 0, reverse=True)
        return all_my_trades

    def fetch_active_oco_orders(self) -> List[Dict[str, Any]]:
        """Obtiene las órdenes OCO activas actualmente en la cuenta de Binance."""
        if not self.client:
            return []
        try:
            open_orders = self.client.fetch_open_orders()
            return [{
                "id": o.get("id"),
                "symbol": o.get("symbol"),
                "type": o.get("type"),
                "side": o.get("side"),
                "price": o.get("price"),
                "stop_price": o.get("stopPrice"),
                "amount": o.get("amount"),
                "status": o.get("status")
            } for o in open_orders]
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []
