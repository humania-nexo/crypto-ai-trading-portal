"""
Telegram Notification Engine for Crypto AI Radar.
Sends real-time trade alerts, TP/SL triggers, and high-conviction scan notifications.
"""

import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id and len(self.bot_token) > 15)

    def send_message(self, message: str) -> bool:
        """Envía un mensaje de texto formateado en HTML a Telegram."""
        if not self.is_configured:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            resp = requests.post(url, json=payload, timeout=8)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def alert_new_opportunity(self, opp: Dict[str, Any]) -> bool:
        """Envía una alerta cuando la IA detecta una oportunidad de Alta Convicción."""
        msg = (
            f"🔥 <b>¡ALERTA RADAR IA: {opp['symbol']}!</b>\n\n"
            f"📌 <b>Patrón:</b> {opp['setup_type']}\n"
            f"💵 <b>Precio Actual:</b> ${opp['price']:,.6f}\n"
            f"🎯 <b>Take Profit:</b> ${opp['take_profit']:,.6f} (+{opp['tp_percent']}%)\n"
            f"🛑 <b>Stop Loss:</b> ${opp['stop_loss']:,.6f} (-{opp['sl_percent']}%)\n"
            f"⚖️ <b>Ratio R:R:</b> 1:{opp['risk_reward_ratio']}\n\n"
            f"📊 <b>Motivo:</b> {opp['technical_reasons'][0] if opp.get('technical_reasons') else 'Confluencia alcista'}"
        )
        return self.send_message(msg)

    def alert_trade_closed(self, trade: Dict[str, Any]) -> bool:
        """Envía una alerta cuando una operación se cierra (por TP o SL)."""
        is_win = trade.get("pnl_usdt", 0) > 0
        icon = "🎉 <b>¡TAKE PROFIT ALCANZADO!</b>" if is_win else "🛑 <b>STOP LOSS EJECUTADO</b>"
        pnl_text = f"+${trade.get('pnl_usdt', 0):,.2f} USDT" if is_win else f"-${abs(trade.get('pnl_usdt', 0)):,.2f} USDT"
        
        msg = (
            f"{icon}\n\n"
            f"🪙 <b>Par:</b> {trade.get('symbol')}\n"
            f"📥 <b>Entrada:</b> ${trade.get('entry_price', 0):,.6f}\n"
            f"📤 <b>Salida:</b> ${trade.get('exit_price', 0):,.6f}\n"
            f"💰 <b>Resultado:</b> {pnl_text} ({trade.get('pnl_percent', 0):+.2f}%)\n"
            f"📋 <b>Motivo:</b> {trade.get('exit_reason')}"
        )
        return self.send_message(msg)
