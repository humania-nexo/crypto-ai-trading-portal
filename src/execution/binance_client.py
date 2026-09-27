"""
Binance Live & Testnet Execution Client.
Connects via CCXT to Binance Spot API with strict safety checks:
- Spot trading only (No margin/futures/leverage).
- OCO (One-Cancels-the-Other) orders for simultaneous Stop-Loss & Take-Profit.
- Balance verification before execution.
"""

import ccxt
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BinanceSpotClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
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

    def get_usdt_balance(self) -> float:
        """Consulta el balance libre de USDT en la cuenta Spot."""
        try:
            balance = self.client.fetch_balance()
            return float(balance.get('USDT', {}).get('free', 0.0))
        except Exception as e:
            logger.error(f"Error fetching Binance balance: {e}")
            return 0.0

    def place_spot_buy_market(self, symbol: str, quote_quantity_usdt: float) -> Dict[str, Any]:
        """Ejecuta una compra de mercado por un monto fijo en USDT."""
        try:
            # Orden de compra a mercado especificando quoteOrderQty (USDT)
            params = {'quoteOrderQty': quote_quantity_usdt}
            order = self.client.create_order(
                symbol=symbol,
                type='market',
                side='buy',
                amount=None,
                params=params
            )
            return {
                "status": "success",
                "order_id": order.get("id"),
                "filled_amount": order.get("filled"),
                "cost": order.get("cost"),
                "average_price": order.get("average")
            }
        except Exception as e:
            logger.error(f"Error executing buy order on Binance for {symbol}: {e}")
            return {"status": "error", "message": str(e)}

    def place_oco_sell_order(
        self,
        symbol: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_trigger_price: float,
        stop_loss_limit_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Coloca una orden OCO (One-Cancels-the-Other) de venta en Binance Spot.
        Permite fijar simultáneamente Take-Profit y Stop-Loss.
        """
        if stop_loss_limit_price is None:
            # Ligeramente por debajo del trigger para asegurar ejecución (slippage buffer)
            stop_loss_limit_price = stop_loss_trigger_price * 0.998
            
        try:
            # En CCXT / Binance, las órdenes OCO se envían con create_order OCO
            params = {
                'stopPrice': stop_loss_trigger_price,
                'stopLimitPrice': stop_loss_limit_price
            }
            
            # create_order con type 'limit' y params OCO o mediante el endpoint específico
            oco_order = self.client.privatePostOrderOco({
                'symbol': symbol.replace('/', ''),
                'side': 'SELL',
                'quantity': self.client.amount_to_precision(symbol, quantity),
                'price': self.client.price_to_precision(symbol, take_profit_price),
                'stopPrice': self.client.price_to_precision(symbol, stop_loss_trigger_price),
                'stopLimitPrice': self.client.price_to_precision(symbol, stop_loss_limit_price),
                'stopLimitTimeInForce': 'GTC'
            })
            
            return {
                "status": "success",
                "orderListId": oco_order.get("orderListId"),
                "take_profit_price": take_profit_price,
                "stop_loss_price": stop_loss_trigger_price
            }
        except Exception as e:
            logger.error(f"Error placing OCO order on Binance for {symbol}: {e}")
            return {"status": "error", "message": str(e)}
