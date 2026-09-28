"""
Crypto Multi-Agent Web Portal & AI Opportunity Radar with Complete Performance Analytics,
Autonomous Pilot Bot, Dynamic Trailing Stop-Loss, Historical Backtesting & Telegram Alerts.
Built with Streamlit & Plotly.
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import time
from datetime import datetime
from dotenv import load_dotenv, set_key

import importlib
import src.analysis.market_scanner
import src.execution.paper_broker
import src.execution.binance_client
import src.analysis.technical_agent
import src.analysis.patterns
import src.risk.risk_manager
import src.notifications.telegram_bot
import src.strategies.auto_trader
import src.analysis.backtester

importlib.reload(src.analysis.market_scanner)
importlib.reload(src.execution.paper_broker)
importlib.reload(src.execution.binance_client)
importlib.reload(src.analysis.technical_agent)
importlib.reload(src.analysis.patterns)
importlib.reload(src.risk.risk_manager)
importlib.reload(src.notifications.telegram_bot)
importlib.reload(src.strategies.auto_trader)
importlib.reload(src.analysis.backtester)

from src.news.sentiment_agent import SentimentAgent
from src.analysis.technical_agent import TechnicalAgent
from src.analysis.indicators import TechnicalIndicators
from src.analysis.patterns import PatternDetector
from src.analysis.market_scanner import MarketScanner, CATEGORIES
from src.risk.risk_manager import RiskManager
from src.execution.paper_broker import PaperBroker
from src.execution.binance_client import BinanceLiveClient
from src.notifications.telegram_bot import TelegramNotifier
from src.strategies.auto_trader import AutoTrader
from src.analysis.backtester import StrategyBacktester

load_dotenv()

# Configuración de página
st.set_page_config(
    page_title="Crypto AI - Radar, Bot Autónomo & Backtesting",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados oscuros y limpios
st.markdown("""
<style>
    .main { background-color: #0b0e14; }
    .stMetric { background-color: #151a23; padding: 12px 18px; border-radius: 10px; border: 1px solid #242c3d; }
    .card-opp { background-color: #151a23; padding: 22px; border-radius: 12px; border: 1px solid #2a364f; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    .card-opp-high { border-left: 6px solid #0ecb81; }
    .card-opp-med { border-left: 6px solid #f0b90b; }
    .badge-high { background-color: rgba(14, 203, 129, 0.15); color: #0ecb81; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; border: 1px solid #0ecb81; }
    .badge-med { background-color: rgba(240, 185, 11, 0.15); color: #f0b90b; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; border: 1px solid #f0b90b; }
    .trade-pill { background-color: #1c2331; padding: 8px 14px; border-radius: 8px; font-size: 13px; border: 1px solid #2b354b; margin-right: 8px; }
    .badge-win { background-color: rgba(14, 203, 129, 0.2); color: #0ecb81; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
    .badge-loss { background-color: rgba(246, 70, 93, 0.2); color: #f6465d; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
    .log-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 12px; font-family: monospace; font-size: 13px; max-height: 250px; overflow-y: auto; color: #58a6ff; }
</style>
""", unsafe_allow_html=True)

# Inicializar agentes, notificador y clientes
def get_agents():
    tech = TechnicalAgent(exchange_id="binance")
    sentiment = SentimentAgent(cryptopanic_api_key=os.getenv("CRYPTOPANIC_API_KEY"))
    broker = PaperBroker(initial_balance=100.0, state_file="paper_trading_state.json")
    risk = RiskManager(max_risk_per_trade_pct=1.0, max_daily_loss_pct=3.0, min_risk_reward_ratio=2.0)
    risk.set_daily_baseline(broker.balance_usdt)
    scanner = MarketScanner(tech, sentiment, risk)
    
    binance_live = BinanceLiveClient(
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_API_SECRET", "")
    )
    
    notifier = TelegramNotifier(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        chat_id=os.getenv("TELEGRAM_CHAT_ID", "")
    )
    
    auto_trader = AutoTrader(
        scanner=scanner,
        broker=broker,
        binance_live=binance_live,
        notifier=notifier
    )
    
    backtester = StrategyBacktester(tech_agent=tech)
    
    return tech, sentiment, risk, broker, scanner, binance_live, notifier, auto_trader, backtester

tech_agent, sentiment_agent, risk_manager, broker, scanner, binance_live, notifier, auto_trader, backtester = get_agents()

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("## 🪙 **Crypto AI Portal**")
    st.caption("Trading Spot Autónomo, Backtesting & Alertas")
    
    # Selector de Modo de Operación
    st.subheader("⚡ Modo de Operación")
    trading_mode = st.radio(
        "Seleccionar Entorno:",
        ["🟢 Cuenta Real de Binance", "🧪 Simulación (Paper Trading)"],
        index=0 if binance_live.is_connected else 1
    )
    
    # Configuración de Claves API de Binance
    with st.expander("🔑 Conexión API de Binance", expanded=not binance_live.is_connected):
        api_k = st.text_input("Binance API Key", value=os.getenv("BINANCE_API_KEY", ""), type="password")
        api_s = st.text_input("Binance Secret Key", value=os.getenv("BINANCE_API_SECRET", ""), type="password")
        
        if st.button("💾 Guardar y Conectar Binance", use_container_width=True):
            if not os.path.exists(".env"):
                with open(".env", "w") as f:
                    f.write("")
            set_key(".env", "BINANCE_API_KEY", api_k)
            set_key(".env", "BINANCE_API_SECRET", api_s)
            st.success("¡Claves guardadas! Recargando...")
            st.rerun()
            
        if binance_live.is_connected:
            st.success("🟢 Conectado a Binance Spot")
        else:
            st.info("Ingresa tus claves para leer tu saldo real en SHIB/USDT y operar.")

    # Configuración de Alertas de Telegram
    with st.expander("📲 Alertas en Tiempo Real (Telegram)", expanded=not notifier.is_configured):
        tg_token = st.text_input("Telegram Bot Token", value=os.getenv("TELEGRAM_BOT_TOKEN", ""), type="password", help="Obtenlo de @BotFather")
        tg_chat = st.text_input("Telegram Chat ID", value=os.getenv("TELEGRAM_CHAT_ID", ""), help="Tu ID numérico de Telegram (ej. de @userinfobot)")
        
        col_tg1, col_tg2 = st.columns(2)
        with col_tg1:
            if st.button("💾 Guardar Telegram", use_container_width=True):
                set_key(".env", "TELEGRAM_BOT_TOKEN", tg_token)
                set_key(".env", "TELEGRAM_CHAT_ID", tg_chat)
                st.success("Configuración guardada.")
                st.rerun()
        with col_tg2:
            if st.button("🔔 Probar Alerta", use_container_width=True):
                temp_notifier = TelegramNotifier(bot_token=tg_token, chat_id=tg_chat)
                ok = temp_notifier.send_message("🚀 <b>¡Conexión Exitosa con Crypto AI Portal!</b>\nRecibirás alertas instantáneas cuando la IA detecte oportunidades de alta probabilidad o se alcance un Take Profit.")
                if ok:
                    st.success("¡Alerta enviada a tu Telegram!")
                else:
                    st.error("Error al enviar mensaje. Verifica el Token y Chat ID.")

    st.subheader("⚙️ Configuración del Escáner")
    scan_timeframe = st.selectbox(
        "Temporalidad de Análisis",
        ["5m (Scalping Rápido < 30 min)", "15m (Intradía 30-90 min)", "1h (Tendencial)", "4h (Swing)"],
        index=0
    )
    tf_clean = scan_timeframe.split()[0]
    
    category_choice = st.selectbox(
        "Universo de Criptomonedas",
        list(CATEGORIES.keys()) + ["⚙️ Selección Manual de Pares"],
        index=0
    )
    
    if category_choice == "⚙️ Selección Manual de Pares":
        all_possible = CATEGORIES["🌐 Top 50 Mercado Completo"]
        selected_pairs_to_scan = st.multiselect("Seleccionar Pares", all_possible, default=all_possible[:10])
    else:
        selected_pairs_to_scan = CATEGORIES[category_choice]
        st.caption(f"Incluye **{len(selected_pairs_to_scan)} criptomonedas** de alta liquidez.")
        
    st.subheader("🎯 Sensibilidad del Escáner")
    sensitivity = st.select_slider(
        "Filtro de Calidad",
        options=["Amplio (Más Opciones)", "Equilibrado (Recomendado)", "Estricto (Solo Top Setups)"],
        value="Equilibrado (Recomendado)"
    )
    threshold_map = {
        "Amplio (Más Opciones)": 0.10,
        "Equilibrado (Recomendado)": 0.18,
        "Estricto (Solo Top Setups)": 0.35
    }
    score_threshold = threshold_map[sensitivity]
    
    st.subheader("🛡️ Gestión de Riesgo")
    risk_pct = st.slider("Riesgo por Operación (%)", 0.5, 3.0, 1.0, 0.1)
    risk_manager.max_risk_per_trade_pct = risk_pct

# --- OBTENER VALUACIÓN PATRIMONIAL COMPLETA ---
portfolio = broker.get_portfolio_summary()

if trading_mode == "🟢 Cuenta Real de Binance" and binance_live.is_connected:
    valuation = binance_live.get_complete_account_valuation()
    total_equity_display = valuation["total_equity_usdt"]
    free_cash_display = valuation["cash_usdt"]
    crypto_val_display = valuation["crypto_value_usdt"]
    active_crypto_assets = valuation["assets"]
    real_open_orders = valuation["open_orders"]
else:
    total_equity_display = portfolio["total_equity_usdt"]
    free_cash_display = portfolio["cash_balance_usdt"]
    crypto_val_display = portfolio["unrealized_pnl_usdt"]
    active_crypto_assets = []
    real_open_orders = []

st.title("🎯 Crypto AI: Radar, Bot Autónomo & Backtesting")
mode_badge = "🟢 CUENTA REAL BINANCE ACTIVA" if (trading_mode == "🟢 Cuenta Real de Binance" and binance_live.is_connected) else "🧪 MODO SIMULACIÓN ACTIVO"
st.caption(f"**Modo Actual:** `{mode_badge}` | Temporalidad: `{tf_clean}` | Universo: `{len(selected_pairs_to_scan)} pares`")

# Fila superior de métricas integrales
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🏦 Patrimonio Total Cuenta", f"${total_equity_display:,.2f} USDT")
c2.metric("💵 USDT Libre (Líquido)", f"${free_cash_display:,.2f} USDT")
c3.metric("🪙 En Criptos / Posiciones", f"${crypto_val_display:,.2f} USDT")
c4.metric("📦 Activos en Posesión", f"{len(active_crypto_assets)} monedas")
c5.metric("📋 Órdenes Abiertas Binance", f"{len(real_open_orders)} órdenes")

st.markdown("---")

# Pestañas principales
tab_radar, tab_bot, tab_backtest, tab_portfolio, tab_analytics, tab_chart, tab_news, tab_binance_guide = st.tabs([
    "🎯 Radar de Oportunidades (< 30 min)",
    "🤖 Piloto Automático (Bot Autónomo)",
    "🧪 Backtesting / Máquina del Tiempo",
    "💼 Mi Portafolio & Activos en Binance",
    "📈 Métricas & Historial de Desempeño",
    "📊 Inspección de Gráfico & Indicadores",
    "📰 Noticias & Sentimiento Global",
    "🛠️ Configuración Exacta en Binance"
])

# =========================================================================
# TAB 1: RADAR DE OPORTUNIDADES
# =========================================================================
with tab_radar:
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        run_scan = st.button("⚡ ESCANEAR MERCADO AHORA", use_container_width=True, type="primary")
    with col_info:
        st.info(f"Escaneando **{len(selected_pairs_to_scan)} criptomonedas** en temporalidad **{tf_clean}** con datos en vivo de Binance (Filtro: {sensitivity}).")
        
    if run_scan or "last_scan_results" not in st.session_state:
        with st.spinner(f"🤖 Analizando {len(selected_pairs_to_scan)} criptomonedas simultáneamente..."):
            st.session_state.last_scan_results = scanner.scan_all_opportunities(
                symbols=selected_pairs_to_scan,
                timeframe=tf_clean,
                min_score_threshold=score_threshold
            )
            
    scan_res = st.session_state.get("last_scan_results", {})
    top_opps = scan_res.get("top_opportunities", [])
    
    st.subheader(f"📋 Opciones de Entrada Detectadas ({len(top_opps)} encontradas)")
    
    if not top_opps:
        st.warning("⏳ En este momento ningún par cumple con los filtros de confluencia alcista en temporalidad 5m. La IA recomienda mantenerse en liquidez.")
    else:
        for idx, opp in enumerate(top_opps):
            is_high = "ALTA" in opp["conviction"]
            border_cls = "card-opp-high" if is_high else "card-opp-med"
            badge_cls = "badge-high" if is_high else "badge-med"
            
            with st.container():
                st.markdown(f"""
                <div class="card-opp {border_cls}">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <div>
                            <span style="font-size: 22px; font-weight: bold; color: white;">{opp['symbol']}</span>
                            <span style="font-size: 16px; color: #848e9c; margin-left: 10px;">Precio Actual: <b>${opp['price']:,.6f}</b></span>
                        </div>
                        <span class="{badge_cls}">{opp['conviction']} (Score: {opp['score']:+.2f})</span>
                    </div>
                    <div style="font-size: 15px; font-weight: 600; color: #38bdf8; margin-bottom: 12px;">
                        📌 Tipo de Entrada: {opp['setup_type']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Desglose de Razones
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    st.markdown("**📊 Razones Técnicas & Figuras:**")
                    for reason in opp["technical_reasons"]:
                        st.markdown(f"- {reason}")
                with col_r2:
                    st.markdown("**📰 Razones Macro & Noticias:**")
                    for f_reason in opp["fundamental_reasons"]:
                        st.markdown(f"- {f_reason}")
                        
                # Plan de Trade OCO
                st.markdown("#### 🎯 Plan de Ejecución con Órdenes OCO (Stop Loss & Take Profit)")
                p1, p2, p3, p4 = st.columns(4)
                p1.metric("📥 Precio Entrada", f"${opp['price']:,.6f}")
                p2.metric("🛑 Stop Loss Sugerido", f"${opp['stop_loss']:,.6f}", f"-{opp['sl_percent']}%", delta_color="inverse")
                p3.metric("🎯 Take Profit Objetivo", f"${opp['take_profit']:,.6f}", f"+{opp['tp_percent']}%")
                p4.metric("⚖️ Ratio Beneficio / Riesgo", f"1 : {opp['risk_reward_ratio']}")
                
                # Botones de Operación
                b_col1, b_col2 = st.columns([1, 2])
                with b_col1:
                    if trading_mode == "🟢 Cuenta Real de Binance" and binance_live.is_connected:
                        max_can_spend = min(10.0, free_cash_display)
                        trade_amount = st.number_input(f"Monto en USDT para {opp['symbol']}", min_value=10.0, max_value=max(10.0, free_cash_display), value=10.0, step=1.0, key=f"amt_{opp['symbol']}")
                        
                        if st.button(f"🚀 COMPRAR EN BINANCE REAL Y PONER OCO ({opp['symbol']})", key=f"real_btn_{opp['symbol']}", type="primary", use_container_width=True):
                            with st.spinner(f"Ejecutando Compra Spot de ${trade_amount:.2f} USDT y configurando orden OCO en Binance..."):
                                exec_res = binance_live.execute_spot_buy_and_oco(
                                    symbol=opp["symbol"],
                                    usdt_amount=trade_amount,
                                    stop_loss_price=opp["stop_loss"],
                                    take_profit_price=opp["take_profit"]
                                )
                                if exec_res["status"] == "success":
                                    st.success(f"✅ ¡Operación Exitosa en Binance! Compra: {exec_res['quantity']} {opp['symbol']} a ${exec_res['entry_price']:.6f}. Orden OCO colocada en Binance.")
                                    # Registrar también en el diario local
                                    broker.open_buy_order(
                                        symbol=opp["symbol"],
                                        price=exec_res["entry_price"],
                                        quantity=exec_res["quantity"],
                                        stop_loss=opp["stop_loss"],
                                        take_profit=opp["take_profit"],
                                        reason=f"Real Binance: {opp['setup_type']}"
                                    )
                                    notifier.alert_new_opportunity(opp)
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error al ejecutar en Binance: {exec_res.get('message', '')}")
                    else:
                        if st.button(f"🧪 Abrir Trade Simulado ({opp['symbol']})", key=f"sim_btn_{opp['symbol']}", use_container_width=True):
                            sim_qty = 50.0 / opp["price"]
                            b_res = broker.open_buy_order(
                                symbol=opp["symbol"],
                                price=opp["price"],
                                quantity=sim_qty,
                                stop_loss=opp["stop_loss"],
                                take_profit=opp["take_profit"],
                                reason=f"Simulación: {opp['setup_type']}"
                            )
                            st.success(f"✅ Posición simulada abierta en {opp['symbol']} a ${opp['price']:,.6f} USDT.")
                            st.rerun()
                st.markdown("---")

# =========================================================================
# TAB 2: PILOTO AUTOMÁTICO (BOT AUTÓNOMO)
# =========================================================================
with tab_bot:
    st.subheader("🤖 Piloto Automático: Bot Inteligente de Trading con Trailing Stop")
    st.markdown("""
    Este bot opera de manera 100% autónoma siguiendo las reglas de análisis cuantitativo del Radar.
    - **Gestión de Trailing Stop**: Al alcanzar el 50% de ganancia hacia el Take Profit, el Stop Loss se mueve automáticamente a **Break-Even (Riesgo Cero)** para blindar tu capital.
    - **Operación con Capital Ficticio o Real**: Puedes dejarlo operando solo con capital simulado para evaluar su rendimiento durante días o semanas antes de habilitar capital real.
    """)
    
    col_bcfg1, col_bcfg2, col_bcfg3 = st.columns(3)
    with col_bcfg1:
        bot_mode_choice = st.selectbox(
            "Modo de Operación del Bot",
            ["🧪 Simulado (Capital Ficticio / Prueba)", "🟢 Real Binance (Con límite estricto de capital)"],
            index=0
        )
        is_bot_real = "Real Binance" in bot_mode_choice
    with col_bcfg2:
        bot_capital_trade = st.number_input("Capital por Operación (USDT)", min_value=10.0, max_value=500.0, value=15.0, step=5.0)
    with col_bcfg3:
        bot_max_pos = st.number_input("Máximo de Posiciones Simultáneas", min_value=1, max_value=10, value=3, step=1)
        
    col_run_bot, col_status_bot = st.columns([1, 2])
    with col_run_bot:
        run_cycle = st.button("▶️ EJECUTAR CICLO AUTÓNOMO AHORA", use_container_width=True, type="primary")
        
    with col_status_bot:
        st.markdown(f"**Estado del Bot:** `🛡️ Trailing Stop Activo` | **Convicción Mínima Requerida:** `ALTA (Score >= 0.35)`")
        
    if "bot_logs" not in st.session_state:
        st.session_state.bot_logs = []
        
    if run_cycle:
        with st.spinner("🤖 El Bot está inspeccionando posiciones abiertas, gestionando Trailing Stops y escaneando nuevas entradas..."):
            cycle_result = auto_trader.run_pilot_cycle(
                symbols=selected_pairs_to_scan,
                timeframe=tf_clean,
                max_active_positions=int(bot_max_pos),
                capital_per_trade_usdt=float(bot_capital_trade),
                is_live_trading=is_bot_real
            )
            for log in cycle_result["logs"]:
                st.session_state.bot_logs.insert(0, f"[{cycle_result['timestamp']}] {log}")
            st.success(f"✅ Ciclo completado a las {cycle_result['timestamp']}. Posiciones activas: {cycle_result['active_positions_count']}")
            
    # Registro de actividad del Bot
    st.markdown("#### 📜 Registro de Decisiones y Trailing Stops en Vivo")
    if st.session_state.bot_logs:
        logs_html = "<br>".join(st.session_state.bot_logs[:20])
        st.markdown(f'<div class="log-box">{logs_html}</div>', unsafe_allow_html=True)
    else:
        st.info("Aún no hay registros de ciclos. Presiona 'EJECUTAR CICLO AUTÓNOMO AHORA' para poner el bot a trabajar.")
        
    st.markdown("---")
    st.subheader("🛡️ Posiciones Actualmente Bajo Supervisión del Bot")
    active_bot_pos = broker.open_positions
    if not active_bot_pos:
        st.caption("No hay posiciones abiertas en este momento.")
    else:
        for sym, p_info in active_bot_pos.items():
            col_p1, col_p2, col_p3, col_p4 = st.columns(4)
            col_p1.metric(f"🪙 {sym}", f"${p_info['entry_price']:,.6f}", "Precio Entrada")
            col_p2.metric("🛑 Stop Loss Actual", f"${p_info['stop_loss']:,.6f}", "Protegido" if p_info['stop_loss'] >= p_info['entry_price'] else "Inicial")
            col_p3.metric("🎯 Take Profit", f"${p_info['take_profit']:,.6f}")
            col_p4.metric("💰 Inversión", f"${(p_info['quantity'] * p_info['entry_price']):,.2f} USDT")

# =========================================================================
# TAB 3: BACKTESTING / MÁQUINA DEL TIEMPO
# =========================================================================
with tab_backtest:
    st.subheader("🧪 Backtesting Histórico: Pon a Prueba la Estrategia en el Pasado")
    st.markdown("""
    Permite simular la estrategia en velas históricas reales de Binance para responder con datos:
    *¿Cuántas operaciones habría ganado el bot? ¿Cuál habría sido la rentabilidad y el riesgo máximo?*
    """)
    
    col_bt1, col_bt2, col_bt3, col_bt4 = st.columns(4)
    with col_bt1:
        bt_symbol = st.selectbox("Criptomoneda a Testear", CATEGORIES["🌐 Top 50 Mercado Completo"], index=0, key="bt_sym")
    with col_bt2:
        bt_tf = st.selectbox("Temporalidad", ["5m", "15m", "1h", "4h"], index=0, key="bt_tf")
    with col_bt3:
        bt_candles = st.slider("Historial de Velas a Analizar", min_value=200, max_value=1000, value=500, step=50)
    with col_bt4:
        bt_trailing = st.checkbox("Activar Trailing Stop a Break-Even", value=True)
        
    col_bt_cap1, col_bt_cap2, col_bt_btn = st.columns([1, 1, 2])
    with col_bt_cap1:
        bt_initial_cap = st.number_input("Capital Inicial ($)", value=1000.0, step=100.0)
    with col_bt_cap2:
        bt_trade_cap = st.number_input("Monto por Trade ($)", value=100.0, step=10.0)
    with col_bt_btn:
        st.write("")
        st.write("")
        run_bt = st.button("🚀 EJECUTAR BACKTEST HISTÓRICO", use_container_width=True, type="primary")
        
    if run_bt or "last_backtest" in st.session_state:
        if run_bt:
            with st.spinner(f"Descargando {bt_candles} velas de Binance y simulando estrategia segundo a segundo..."):
                st.session_state.last_backtest = backtester.run_backtest(
                    symbol=bt_symbol,
                    timeframe=bt_tf,
                    total_candles=bt_candles,
                    initial_capital=float(bt_initial_cap),
                    capital_per_trade_usdt=float(bt_trade_cap),
                    min_score_threshold=0.30,
                    enable_trailing_breakeven=bt_trailing
                )
                
        bt_res = st.session_state.get("last_backtest", {})
        if "error" in bt_res:
            st.error(bt_res["error"])
        elif bt_res:
            st.markdown(f"### 📊 Resultados de la Simulación ({bt_res['symbol']} • {bt_res['timeframe']})")
            st.caption(f"Periodo Analizado: `{bt_res['start_date']}` hasta `{bt_res['end_date']}` ({bt_res['total_candles_analyzed']} velas)")
            
            # Fila de KPIs
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.metric("🎯 Tasa de Acierto (Win Rate)", f"{bt_res['win_rate_pct']}%", f"{bt_res['win_trades']}W / {bt_res['loss_trades']}L")
            k2.metric("💰 Ganancia Neta PnL", f"${bt_res['net_pnl_usdt']:+,.2f} USDT", f"{bt_res['net_return_pct']:+.2f}%")
            k3.metric("📈 Factor de Beneficio", f"{bt_res['profit_factor']:.2f}")
            k4.metric("🛡️ Máximo Drawdown", f"{bt_res['max_drawdown_pct']:.2f}%", delta_color="inverse")
            k5.metric("📋 Total de Operaciones", f"{bt_res['total_trades']}")
            k6.metric("💵 Ganancia Media / Trade", f"${bt_res['avg_trade_pnl_usdt']:+,.2f}")
            
            # Gráfico de Curva de Capital (Equity Curve)
            eq_df = pd.DataFrame(bt_res["equity_curve"])
            if not eq_df.empty:
                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(
                    x=eq_df["timestamp"],
                    y=eq_df["equity"],
                    mode="lines",
                    line=dict(color="#0ecb81" if bt_res["net_pnl_usdt"] >= 0 else "#f6465d", width=2),
                    name="Capital de la Cuenta ($)"
                ))
                fig_eq.update_layout(
                    title="📈 Evolución del Capital a lo largo del tiempo (Equity Curve)",
                    paper_bgcolor="#151a23",
                    plot_bgcolor="#0e131b",
                    font=dict(color="#d1d4dc"),
                    height=350,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_eq, use_container_width=True)
                
            # Tabla de Operaciones Simuladas
            st.markdown("#### 📜 Registro de Operaciones del Backtesting")
            if bt_res["trades"]:
                st.dataframe(pd.DataFrame(bt_res["trades"]), use_container_width=True)
            else:
                st.info("No se generaron operaciones en el periodo analizado con los filtros actuales.")

# =========================================================================
# TAB 4: MI PORTAFOLIO & ACTIVOS EN BINANCE
# =========================================================================
with tab_portfolio:
    st.subheader("💼 Distribución Completa de Patrimonio en Binance")
    
    if trading_mode == "🟢 Cuenta Real de Binance" and binance_live.is_connected:
        st.markdown("### 🪙 Criptomonedas en Posesión")
        if not active_crypto_assets:
            st.info("No se detectaron balances de criptomonedas distintos a USDT.")
            asset_rows = []
            for a in active_crypto_assets:
                free_amt = float(a.get("free_amount", a.get("free", 0.0)))
                locked_amt = float(a.get("locked_in_orders", a.get("locked", 0.0)))
                total_amt = float(a.get("total_amount", a.get("total", 0.0)))
                u_price = float(a.get("unit_price_usdt", a.get("current_price", 0.0)))
                val_usd = float(a.get("value_usdt", 0.0))
                pct = a.get("percentage", 0.0)
                
                u_price_str = f"${u_price:,.8f}" if u_price < 1.0 else f"${u_price:,.4f}"
                
                asset_rows.append({
                    "Criptomoneda": a.get("asset", ""),
                    "Cantidad Libre": f"{free_amt:,.6f}",
                    "Cantidad Bloqueada (en Órdenes)": f"{locked_amt:,.6f}",
                    "Cantidad Total": f"{total_amt:,.6f}",
                    "Precio Unitario": u_price_str,
                    "Valor Estimado (USD)": f"${val_usd:,.2f} USDT",
                    "% del Portafolio": f"{pct}%"
                })
            st.dataframe(pd.DataFrame(asset_rows), use_container_width=True)
            
        st.markdown("---")
        st.markdown("### 📋 Órdenes Activas en Binance (Incluyendo OCO)")
        if not real_open_orders:
            st.info("No hay órdenes de compra/venta pendientes ni órdenes OCO abiertas en Binance.")
        else:
            order_rows = []
            for o in real_open_orders:
                order_rows.append({
                    "Par": o.get("symbol"),
                    "Tipo": o.get("type"),
                    "Lado": o.get("side"),
                    "Precio Límite": f"${float(o.get('price', 0)):,.6f}",
                    "Precio Stop Trigger": f"${float(o.get('stopPrice', 0)):,.6f}" if o.get('stopPrice') else "N/A",
                    "Cantidad": f"{float(o.get('amount', 0)):,.4f}",
                    "Estado": o.get("status")
                })
            st.dataframe(pd.DataFrame(order_rows), use_container_width=True)
    else:
        st.info("Actualmente estás en Modo Simulación. Cambia a '🟢 Cuenta Real de Binance' en la barra lateral para ver tus balances reales de SHIB, BNB y USDT.")

# =========================================================================
# TAB 5: MÉTRICAS & HISTORIAL DE DESEMPEÑO
# =========================================================================
with tab_analytics:
    st.subheader("📈 Métricas & Historial de Desempeño")
    
    analytics = broker.get_performance_analytics()
    trades = broker.trade_history
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🎯 Win Rate (Efectividad)", f"{analytics['win_rate_pct']}%", f"{analytics['winning_trades']}W / {analytics['losing_trades']}L")
    m2.metric("💰 Ganancia Total Neta", f"${analytics['total_pnl_usdt']:+,.2f} USDT", f"{analytics['net_roi_pct']:+.2f}% ROI")
    m3.metric("📈 Factor de Beneficio", f"{analytics['profit_factor']:.2f}")
    m4.metric("🏆 Mejor Operación", f"${analytics['best_trade_usdt']:+,.2f} USDT")
    m5.metric("🛑 Peor Operación", f"${analytics['worst_trade_usdt']:+,.2f} USDT", delta_color="inverse")
    
    st.markdown("---")
    
    if not trades:
        st.info("Aún no has cerrado operaciones en el historial. A medida que operes manualmente o con el bot, aquí se generará tu curva de rendimiento y estadísticas.")
    else:
        eq_data = []
        running_equity = 100.0
        for t in trades:
            running_equity += t.get("pnl_usdt", 0)
            eq_data.append({"date": t.get("exit_time", ""), "equity": running_equity})
            
        if eq_data:
            df_eq = pd.DataFrame(eq_data)
            fig_j = go.Figure()
            fig_j.add_trace(go.Scatter(x=df_eq["date"], y=df_eq["equity"], mode="lines+markers", line=dict(color="#0ecb81", width=2), name="Patrimonio ($)"))
            fig_j.update_layout(title="📈 Curva de Crecimiento de Capital Real/Simulado (Equity Curve)", paper_bgcolor="#151a23", plot_bgcolor="#0e131b", font=dict(color="#d1d4dc"), height=300)
            st.plotly_chart(fig_j, use_container_width=True)
            
        st.subheader("📜 Diario Detallado de Operaciones Cerradas")
        df_journal = []
        for i, t in enumerate(trades):
            is_win = t.get("pnl_usdt", 0) > 0
            ep = t.get("entry_price", 0)
            xp = t.get("exit_price", 0)
            ep_str = f"${ep:,.8f}" if ep < 1.0 else f"${ep:,.4f}"
            xp_str = f"${xp:,.8f}" if xp < 1.0 else f"${xp:,.4f}"
            
            df_journal.append({
                "#": i + 1,
                "Fecha / Hora": str(t.get("exit_time", ""))[:16].replace("T", " "),
                "Criptomoneda": t.get("symbol", ""),
                "Precio Entrada": ep_str,
                "Precio Salida": xp_str,
                "Motivo": f"🎯 {t.get('exit_reason')}" if is_win else f"🛑 {t.get('exit_reason')}",
                "PnL ($)": f"{'+' if is_win else ''}${t.get('pnl_usdt', 0):.4f} USDT",
                "Retorno (%)": f"{'+' if is_win else ''}{t.get('pnl_percent', 0):.2f}%",
                "Estrategia": t.get("signal_reason", "")
            })
        st.dataframe(pd.DataFrame(df_journal), use_container_width=True)

# =========================================================================
# TAB 6: INSPECCIÓN DETALLADA DE GRÁFICO
# =========================================================================
with tab_chart:
    st.subheader("🔍 Inspección Gráfica Detallada")
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        inspect_pair = st.selectbox("Seleccionar Criptomoneda para Inspección", CATEGORIES["🌐 Top 50 Mercado Completo"], index=0)
    with col_sel2:
        inspect_tf = st.selectbox("Temporalidad del Gráfico", ["5m", "15m", "1h", "4h", "1d"], index=0)
        
    df_chart_raw = tech_agent.fetch_ohlcv(symbol=inspect_pair, timeframe=inspect_tf, limit=120)
    if not df_chart_raw.empty:
        df_chart = TechnicalIndicators.calculate_all(df_chart_raw)
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])
        
        # Velas
        fig.add_trace(go.Candlestick(
            x=df_chart['datetime'], open=df_chart['open'], high=df_chart['high'],
            low=df_chart['low'], close=df_chart['close'], name='Precio'
        ), row=1, col=1)
        
        # EMAs
        fig.add_trace(go.Scatter(x=df_chart['datetime'], y=df_chart['ema_20'], line=dict(color='#f0b90b', width=1.5), name='EMA 20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart['datetime'], y=df_chart['ema_50'], line=dict(color='#0ecb81', width=1.5), name='EMA 50'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart['datetime'], y=df_chart['ema_200'], line=dict(color='#8b5cf6', width=2), name='EMA 200'), row=1, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(x=df_chart['datetime'], y=df_chart['rsi'], line=dict(color='#38bdf8', width=1.5), name='RSI (14)'), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#f87171", line_width=1, row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#4ade80", line_width=1, row=2, col=1)
        
        # MACD
        fig.add_trace(go.Scatter(x=df_chart['datetime'], y=df_chart['macd'], line=dict(color='#0ecb81', width=1.5), name='MACD'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_chart['datetime'], y=df_chart['macd_signal'], line=dict(color='#f6465d', width=1.5), name='Signal'), row=3, col=1)
        fig.add_trace(go.Bar(x=df_chart['datetime'], y=df_chart['macd_hist'], marker_color=['#0ecb81' if v >= 0 else '#f6465d' for v in df_chart['macd_hist']], name='Hist'), row=3, col=1)
        
        fig.update_layout(
            height=600, margin=dict(l=10, r=10, t=10, b=10),
            xaxis_rangeslider_visible=False, paper_bgcolor="#151a23", plot_bgcolor="#0e131b", font={'color': "#d1d4dc"}
        )
        st.plotly_chart(fig, use_container_width=True)

# =========================================================================
# TAB 7: NOTICIAS & SENTIMIENTO GLOBAL
# =========================================================================
with tab_news:
    st.subheader("🧭 Contexto Fundamental y Sentimiento Global")
    sent_data = sentiment_agent.get_market_sentiment_summary()
    fng = sent_data["fear_and_greed"]
    
    col_g, col_nw = st.columns([1, 2])
    with col_g:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=fng["score"],
            title={'text': f"Fear & Greed: {fng['sentiment']}", 'font': {'size': 18}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': "#0ecb81" if fng["score"] >= 60 else ("#f6465d" if fng["score"] <= 40 else "#f0b90b")},
                'steps': [
                    {'range': [0, 25], 'color': '#8B0000'},
                    {'range': [25, 45], 'color': '#f6465d'},
                    {'range': [45, 55], 'color': '#707a8a'},
                    {'range': [55, 75], 'color': '#0ecb81'},
                    {'range': [75, 100], 'color': '#006400'}
                ]
            }
        ))
        fig_gauge.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="#151a23", font={'color': "white"})
        st.plotly_chart(fig_gauge, use_container_width=True)
        
    with col_nw:
        for news_item in sent_data.get("recent_headlines", []):
            st.markdown(f"""
            <div style="background-color: #151a23; padding: 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #242c3d;">
                <div style="font-size: 11px; color: #94a3b8;">{news_item['source']} • {news_item.get('published', '')[:16]}</div>
                <div style="font-weight: 500; font-size: 14px; margin-top: 4px;">
                    <a href="{news_item['link']}" target="_blank" style="color: #38bdf8; text-decoration: none;">{news_item['title']}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

# =========================================================================
# TAB 8: GUÍA DE CONFIGURACIÓN PASO A PASO EN BINANCE
# =========================================================================
with tab_binance_guide:
    st.subheader("🛠️ Cómo Configurar tu Gráfico de Binance para ver lo mismo que la IA")
    st.markdown("""
    Para que puedas corroborar visualmente cada señal que te propone el agente en tu pantalla de Binance, sigue estos pasos para configurar la vista **TradingView** de Binance con los mismos parámetros exactos:
    """)
    
    st.markdown("""
    ### ⏱️ 1. Temporalidad (Para operaciones < 30 minutos)
    - En el gráfico de Binance, selecciona arriba la temporalidad **`5m`** (5 minutos).
    - *Razón*: Cada vela representa 5 minutos. Un trade típico de 3 a 6 velas dura entre **15 y 30 minutos**.
    
    ---
    
    ### 📈 2. Medias Móviles Exponenciales (EMA)
    Haz clic en el botón de **Indicadores Técnicos (icono de `fx` o compás)** en Binance y busca **`EMA` (Moving Average Exponential)**. Agrégala 3 veces con esta configuración:
    
    | Indicador | Longitud (Periodo) | Color Recomendado | ¿Qué representa para la IA? |
    | :--- | :--- | :--- | :--- |
    | **EMA 1** | **`20`** | 🟡 **Amarillo** | Tendencia rápida de corto plazo (gatillo de entrada). |
    | **EMA 2** | **`50`** | 🟢 **Verde** | Soporte dinámico intermedio (zona de rebote). |
    | **EMA 3** | **`200`** | 🟣 **Morado** | Tendencia principal. Si el precio está arriba, solo se compran largos. |
    
    ---
    
    ### 📊 3. RSI (Relative Strength Index)
    En el menú de indicadores, busca **`RSI`**:
    - **Longitud (Length)**: **`14`**
    - **Nivel de Sobrecompra (Upper Band)**: **`70`** (Color Rojo)
    - **Nivel Medio (Middle Band)**: **`50`**
    - **Nivel de Sobreventa (Lower Band)**: **`30`** (Color Verde)
    - *¿Qué ve la IA?*: Si el RSI toca 30-35 en velas de 5m y rebota, es una zona de compra con descuento. Si está entre 45 y 60, confirma impulso alcista sano.
    
    ---
    
    ### ⚡ 4. MACD (Moving Average Convergence Divergence)
    En el menú de indicadores, busca **`MACD`**:
    - **Fast Length (Longitud Rápida)**: **`12`**
    - **Slow Length (Longitud Lenta)**: **`26`**
    - **Signal Smoothing (Señal)**: **`9`**
    - *¿Qué ve la IA?*: El "Cruce Dorado" ocurre cuando la línea azul rápida cruza hacia arriba a la línea naranja/roja lenta y el histograma pasa a verde.
    
    ---
    
    ### 🎯 5. Cómo colocar la orden en Binance (OCO)
    Cuando decidas entrar en una oportunidad aprobada:
    1. Compras la cantidad deseada a precio de **Mercado (Market)** en Binance Spot.
    2. Inmediatamente después, vas a la pestaña **Vender (Sell)** y seleccionas el tipo de orden **`OCO`**:
       - En **Precio (Limit)**: Escribes el **Take Profit** sugerido por la IA.
       - En **Stop**: Escribes el **Stop Loss Trigger** sugerido por la IA.
       - En **Límite**: Escribes un valor ligeramente inferior al Stop (o el mismo Stop Loss).
    3. Haces clic en **Vender**. ¡Listo! Si el precio sube al TP ganas, si baja al SL se corta la pérdida y la otra orden se cancela sola.
    """)
