"""
24/7 Autonomous Market Watcher & Telegram Alert Daemon.
Designed for lightweight cloud deployment (Render, Railway, VPS, etc.).
Requires NO Binance API keys (uses only public market data).
Scans Binance Spot pairs and dispatches high-conviction scalping alerts directly to your Telegram.
"""

import os
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from typing import Dict, Set
from dotenv import load_dotenv

from src.analysis.technical_agent import TechnicalAgent
from src.news.sentiment_agent import SentimentAgent
from src.risk.risk_manager import RiskManager
from src.analysis.market_scanner import MarketScanner, CATEGORIES
from src.notifications.telegram_bot import TelegramNotifier

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("WatcherDaemon")

load_dotenv()

# Servidor HTTP ligero para que Render reconozca el servicio web activo
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK - Crypto AI Watcher Daemon Running 24/7")
        
    def log_message(self, format, *args):
        pass # Silenciar logs de health check

class MarketWatcherDaemon:
    def __init__(
        self,
        timeframe: str = "5m",
        scan_interval_seconds: int = 180, # Cada 3 minutos
        min_score_threshold: float = 0.30, # Umbral equilibrado de convicción
        alert_cooldown_minutes: int = 45   # Evitar repetir alerta del mismo par en 45 min
    ):
        self.timeframe = timeframe
        self.scan_interval = scan_interval_seconds
        self.min_score_threshold = min_score_threshold
        self.alert_cooldown = timedelta(minutes=alert_cooldown_minutes)
        
        # Inicializar agentes (públicos, sin claves de Binance)
        self.tech = TechnicalAgent(exchange_id="binance")
        self.sentiment = SentimentAgent(cryptopanic_api_key=os.getenv("CRYPTOPANIC_API_KEY"))
        self.risk = RiskManager(max_risk_per_trade_pct=1.0, min_risk_reward_ratio=2.0)
        self.scanner = MarketScanner(self.tech, self.sentiment, self.risk)
        
        # Notificador de Telegram
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
        
        # Registro de enfriamiento de alertas (symbol -> last_alert_time)
        self.last_alerts: Dict[str, datetime] = {}
        
        # Universo de pares a vigilar
        self.symbols = CATEGORIES["🌐 Top 50 Mercado Completo"]

    def can_alert(self, symbol: str) -> bool:
        """Verifica que no hayamos alertado este mismo par recientemente para evitar spam."""
        if symbol not in self.last_alerts:
            return True
        return (datetime.utcnow() - self.last_alerts[symbol]) >= self.alert_cooldown

    def send_rich_signal_alert(self, opp: Dict) -> bool:
        """Envía un mensaje detallado a Telegram con el plan de ejecución listo para usar en la app de Binance."""
        sym = opp["symbol"]
        price = opp["price"]
        sl = opp["stop_loss"]
        tp = opp["take_profit"]
        sl_pct = opp["sl_percent"]
        tp_pct = opp["tp_percent"]
        rr = opp["risk_reward_ratio"]
        setup = opp["setup_type"]
        
        p_str = f"${price:,.8f}" if price < 1.0 else f"${price:,.4f}"
        sl_str = f"${sl:,.8f}" if sl < 1.0 else f"${sl:,.4f}"
        tp_str = f"${tp:,.8f}" if tp < 1.0 else f"${tp:,.4f}"
        
        tech_reasons = "\n".join([f"• {r}" for r in opp.get("technical_reasons", [])[:2]])
        
        # Calcular hitos de Trailing Stop
        target_gain = tp - price
        be_trig = price + (target_gain * 0.50)
        be_sl = price * 1.001
        ts_trig = price + (target_gain * 0.75)
        ts_sl = price + (target_gain * 0.40)
        
        be_trig_str = f"${be_trig:,.8f}" if be_trig < 1.0 else f"${be_trig:,.4f}"
        be_sl_str = f"${be_sl:,.8f}" if be_sl < 1.0 else f"${be_sl:,.4f}"
        ts_trig_str = f"${ts_trig:,.8f}" if ts_trig < 1.0 else f"${ts_trig:,.4f}"
        ts_sl_str = f"${ts_sl:,.8f}" if ts_sl < 1.0 else f"${ts_sl:,.4f}"
        
        msg = (
            f"🔥 <b>¡NUEVA OPORTUNIDAD EN {sym}!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Patrón:</b> {setup}\n"
            f"💵 <b>Precio Actual:</b> <code>{p_str}</code>\n\n"
            f"🎯 <b>Take Profit (Objetivo):</b> <code>{tp_str}</code> (+{tp_pct}%)\n"
            f"🛑 <b>Stop Loss (Inicial):</b> <code>{sl_str}</code> (-{sl_pct}%)\n"
            f"⚖️ <b>Ratio Riesgo/Beneficio:</b> 1 : {rr}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ <b>Hitos de Trailing Stop y Protección:</b>\n"
            f"• <b>Break-Even (Riesgo 0):</b> Al llegar a <code>{be_trig_str}</code> ➔ Subir SL a <code>{be_sl_str}</code>\n"
            f"• <b>Trailing (+40% Lock):</b> Al llegar a <code>{ts_trig_str}</code> ➔ Subir SL a <code>{ts_sl_str}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Análisis Técnico:</b>\n{tech_reasons}\n\n"
            f"📱 <b>Cómo ejecutar en tu app de Binance:</b>\n"
            f"1. Compra <b>{sym}</b> a precio de Mercado.\n"
            f"2. En Vender, pon orden <b>OCO</b> con:\n"
            f"   • Limit: <code>{tp_str}</code>\n"
            f"   • Stop: <code>{sl_str}</code>\n"
            f"   • Limit: <code>{sl_str}</code>"
        )
        
        ok = self.notifier.send_message(msg)
        if ok:
            self.last_alerts[sym] = datetime.utcnow()
            logger.info(f"✅ Alerta enviada con éxito a Telegram para {sym}")
        return ok

    def run_single_scan(self):
        """Ejecuta una ronda de escaneo completa."""
        logger.info(f"🔍 Escaneando {len(self.symbols)} pares en temporalidad {self.timeframe}...")
        try:
            results = self.scanner.scan_all_opportunities(
                symbols=self.symbols,
                timeframe=self.timeframe,
                min_score_threshold=self.min_score_threshold
            )
            top_opps = results.get("top_opportunities", [])
            logger.info(f"✨ Escaneo finalizado. Se encontraron {len(top_opps)} oportunidades.")
            
            for opp in top_opps:
                sym = opp["symbol"]
                if self.can_alert(sym):
                    logger.info(f"📢 Despachando alerta para {sym} (Score: {opp['score']:+.2f})...")
                    self.send_rich_signal_alert(opp)
                else:
                    logger.info(f"⏳ {sym} está en periodo de enfriamiento antispam. Omitiendo re-alerta.")
        except Exception as e:
            logger.error(f"❌ Error durante el ciclo de escaneo: {e}")

    def loop(self):
        """Bucle continuo de escaneo cada N segundos."""
        logger.info("=" * 60)
        logger.info("🤖 VIGILANTE AUTÓNOMO INICIADO Y EN MONITOREO CONTINUO")
        logger.info(f"⏱️ Intervalo de escaneo: cada {self.scan_interval // 60} minutos")
        logger.info("=" * 60)
        
        while True:
            self.run_single_scan()
            logger.info(f"💤 Esperando {self.scan_interval} segundos para el próximo ciclo...")
            time.sleep(self.scan_interval)

if __name__ == "__main__":
    watcher = MarketWatcherDaemon(
        timeframe="5m",
        scan_interval_seconds=180, # Escaneo cada 3 minutos
        min_score_threshold=0.30,  # Oportunidades claras
        alert_cooldown_minutes=45  # Cooldown de 45 min por par
    )
    
    # Iniciar escáner en segundo plano
    scanner_thread = threading.Thread(target=watcher.loop, daemon=True)
    scanner_thread.start()
    
    # Mantener servidor web activo en el hilo principal para responder a Render
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 Servidor Web de Render escuchando en el puerto {port}")
    httpd = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    httpd.serve_forever()
