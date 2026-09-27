"""
Main Crypto Agent Orchestrator & Terminal Dashboard.
Runs the multi-agent system, displays live analysis, news, and paper trading portfolio.
"""

import time
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Asegurar codificación UTF-8 en terminal de Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich import box

from src.news.sentiment_agent import SentimentAgent
from src.analysis.technical_agent import TechnicalAgent
from src.risk.risk_manager import RiskManager
from src.execution.paper_broker import PaperBroker
from src.strategies.strategy_synthesizer import StrategySynthesizer

load_dotenv()

console = Console(highlight=False)

def create_dashboard():
    # Inicialización de agentes
    tech_agent = TechnicalAgent(exchange_id="binance")
    sentiment_agent = SentimentAgent(cryptopanic_api_key=os.getenv("CRYPTOPANIC_API_KEY"))
    risk_manager = RiskManager(
        max_risk_per_trade_pct=float(os.getenv("MAX_RISK_PER_TRADE_PERCENT", 1.0)),
        max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PERCENT", 3.0)),
        min_risk_reward_ratio=2.0
    )
    broker = PaperBroker(
        initial_balance=float(os.getenv("INITIAL_PAPER_BALANCE", 100.0)),
        state_file="paper_trading_state.json"
    )
    
    # Establecer línea base de balance diario
    risk_manager.set_daily_baseline(broker.balance_usdt)
    
    synthesizer = StrategySynthesizer(
        tech_agent=tech_agent,
        sentiment_agent=sentiment_agent,
        risk_manager=risk_manager,
        broker=broker
    )
    
    symbols = [s.strip() for s in os.getenv("TRADING_PAIRS", "BTC/USDT,ETH/USDT,SOL/USDT").split(",")]
    timeframe = os.getenv("DEFAULT_TIMEFRAME", "15m")
    
    console.print(Panel.fit(
        "[bold cyan]🤖 SISTEMA MULTI-AGENTE DE ANÁLISIS & TRADING CRIPTO[/bold cyan]\n"
        f"[green]• Modo:[/green] Paper Trading (Simulado) | [green]• Temporalidad:[/green] {timeframe}\n"
        f"[green]• Gestión de Riesgo:[/green] Stop-Loss Obligatorio | R:R Mínimo 1:2 | Cero Apalancamiento",
        border_style="cyan"
    ))
    
    # 1. Obtener Sentimiento del Mercado y Noticias
    with console.status("[bold yellow]Agente de Noticias escaneando titulares y Fear & Greed Index...[/bold yellow]"):
        sentiment_data = sentiment_agent.get_market_sentiment_summary()
        
    fng = sentiment_data["fear_and_greed"]
    fng_color = "green" if fng["score"] >= 60 else ("red" if fng["score"] <= 40 else "yellow")
    
    news_table = Table(title="📰 SENTIMIENTO Y NOTICIAS EN VIVO", box=box.ROUNDED, expand=True)
    news_table.add_column("Fuente", style="cyan", width=14)
    news_table.add_column("Titular", style="white")
    news_table.add_column("Sentimiento", justify="center", width=12)
    
    for item in sentiment_data.get("recent_headlines", [])[:4]:
        sent_color = "green" if item["sentiment"] == "BULLISH" else ("red" if item["sentiment"] == "BEARISH" else "yellow")
        news_table.add_row(item["source"], item["title"][:75] + "...", f"[{sent_color}]{item['sentiment']}[/{sent_color}]")
        
    console.print(f"\n📊 [bold]Fear & Greed Index:[/bold] [{fng_color}]{fng['score']}/100 ({fng['sentiment']})[/{fng_color}] | [bold]Sentimiento General Noticias:[/bold] [cyan]{sentiment_data['overall_sentiment']}[/cyan] (Score: {sentiment_data['overall_score']})")
    console.print(news_table)
    
    # 2. Análisis Técnico y Toma de Decisiones
    tech_table = Table(title=f"📈 ANÁLISIS TÉCNICO & SEÑALES ({timeframe})", box=box.ROUNDED, expand=True)
    tech_table.add_column("Par", style="bold yellow")
    tech_table.add_column("Precio Actual", justify="right")
    tech_table.add_column("Tendencia", justify="center")
    tech_table.add_column("RSI (14)", justify="center")
    tech_table.add_column("MACD", justify="center")
    tech_table.add_column("Patrones", justify="left")
    tech_table.add_column("Decisión Agente", justify="center")
    
    current_prices = {}
    
    for sym in symbols:
        with console.status(f"[bold yellow]Analizando {sym}...[/bold yellow]"):
            res = synthesizer.evaluate_market_and_execute(sym, timeframe=timeframe)
            
        current_prices[sym] = res["current_price"]
        tech_an = tech_agent.analyze_pair(sym, timeframe=timeframe)
        sig = tech_an.get("signals", {})
        
        patterns_str = ", ".join([p["pattern"] for p in tech_an.get("patterns", [])]) or "Sin patrón clave"
        
        # Color coding
        rsi_val = sig.get("rsi", 50)
        rsi_col = "red" if rsi_val >= 70 else ("green" if rsi_val <= 30 else "white")
        
        act_col = "green" if "BUY" in res["action"] else ("yellow" if res["action"] == "HOLD" else "red")
        
        tech_table.add_row(
            sym,
            f"${res['current_price']:,.2f}",
            sig.get("trend", "N/A"),
            f"[{rsi_col}]{rsi_val:.1f}[/{rsi_col}]",
            sig.get("macd_crossover", "N/A"),
            patterns_str,
            f"[{act_col}]{res['action']}[/{act_col}]"
        )
        
    console.print(tech_table)
    
    # 3. Estado del Portafolio Simulado (Paper Trading)
    portfolio = broker.get_portfolio_summary(current_prices)
    
    port_panel = (
        f"[bold]💰 Balance Disponible:[/bold] ${portfolio['cash_balance_usdt']:,.2f} USDT  |  "
        f"[bold]🏦 Patrimonio Total:[/bold] ${portfolio['total_equity_usdt']:,.2f} USDT  |  "
        f"[bold]📈 PnL No Realizado:[/bold] {'+' if portfolio['unrealized_pnl_usdt'] >= 0 else ''}${portfolio['unrealized_pnl_usdt']:,.2f} USDT  |  "
        f"[bold]🏆 Win Rate:[/bold] {portfolio['win_rate']:.1f}% ({portfolio['total_trades']} trades cerrados)"
    )
    console.print(Panel(port_panel, title="💼 RESUMEN DEL PORTAFOLIO (PAPER TRADING)", border_style="green"))
    
    if portfolio["open_positions"]:
        pos_table = Table(title="🟢 POSICIONES ABIERTAS (CON SL & TP SIMULTÁNEO)", box=box.ROUNDED, expand=True)
        pos_table.add_column("Par", style="yellow")
        pos_table.add_column("Entrada", justify="right")
        pos_table.add_column("Precio Actual", justify="right")
        pos_table.add_column("Stop Loss (SL)", justify="right", style="red")
        pos_table.add_column("Take Profit (TP)", justify="right", style="green")
        pos_table.add_column("PnL Actual", justify="right")
        
        for pos in portfolio["open_positions"]:
            pnl_col = "green" if pos["unrealized_pnl_usdt"] >= 0 else "red"
            pos_table.add_row(
                pos["symbol"],
                f"${pos['entry_price']:,.2f}",
                f"${pos['current_price']:,.2f}",
                f"${pos['stop_loss']:,.2f}",
                f"${pos['take_profit']:,.2f}",
                f"[{pnl_col}]{'+' if pos['unrealized_pnl_usdt'] >= 0 else ''}${pos['unrealized_pnl_usdt']:.2f} ({pos['unrealized_pnl_pct']:+.2f}%)[/{pnl_col}]"
            )
        console.print(pos_table)
    else:
        console.print("[dim italic]No hay posiciones abiertas en este momento. El agente estratega está esperando una oportunidad de alta confluencia.[/dim italic]\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Crypto Multi-Agent Bot")
    parser.add_argument("--loop", action="store_true", help="Ejecutar en bucle continuo cada N segundos")
    parser.add_argument("--interval", type=int, default=60, help="Intervalo en segundos para el modo bucle")
    args = parser.parse_args()
    
    if args.loop:
        console.print(f"[bold green]Iniciando bucle de monitoreo continuo (cada {args.interval}s)... Presiona Ctrl+C para detener.[/bold green]\n")
        try:
            while True:
                create_dashboard()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Bot detenido de forma segura por el usuario.[/bold yellow]")
    else:
        create_dashboard()
