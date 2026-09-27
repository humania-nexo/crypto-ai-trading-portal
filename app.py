"""
Crypto Multi-Agent Web Portal & AI Opportunity Radar with Complete Performance Analytics & Trading Journal.
Built with Streamlit & Plotly.
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime
from dotenv import load_dotenv, set_key

import importlib
import src.analysis.market_scanner
import src.execution.paper_broker
import src.execution.binance_client
import src.analysis.technical_agent
import src.analysis.patterns
import src.risk.risk_manager

importlib.reload(src.analysis.market_scanner)
importlib.reload(src.execution.paper_broker)
importlib.reload(src.execution.binance_client)
importlib.reload(src.analysis.technical_agent)
importlib.reload(src.analysis.patterns)
importlib.reload(src.risk.risk_manager)

from src.news.sentiment_agent import SentimentAgent
from src.analysis.technical_agent import TechnicalAgent
from src.analysis.indicators import TechnicalIndicators
from src.analysis.patterns import PatternDetector
from src.analysis.market_scanner import MarketScanner, CATEGORIES
from src.risk.risk_manager import RiskManager
from src.execution.paper_broker import PaperBroker
from src.execution.binance_client import BinanceLiveClient

load_dotenv()

# Configuración de página
st.set_page_config(
    page_title="Crypto AI - Radar & Trading Real",
    page_icon="🎯",
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
</style>
""", unsafe_allow_html=True)

# Inicializar agentes y clientes
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
    return tech, sentiment, risk, broker, scanner, binance_live

tech_agent, sentiment_agent, risk_manager, broker, scanner, binance_live = get_agents()

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("## 🪙 **Crypto AI Radar**")
    st.caption("Asistente Autónomo de Análisis & Trading Real")
    
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
            st.success("🟢 Claves configuradas activas")
        else:
            st.info("Ingresa tus claves para leer tu saldo real en SHIB/USDT y operar.")

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

st.title("🎯 Radar de Oportunidades & Portafolio Real Binance")
mode_badge = "🟢 CUENTA REAL BINANCE ACTIVA" if (trading_mode == "🟢 Cuenta Real de Binance" and binance_live.is_connected) else "🧪 MODO SIMULACIÓN ACTIVO"
st.caption(f"**Modo Actual:** `{mode_badge}` | Temporalidad: `{tf_clean}` | Escaneando `{len(selected_pairs_to_scan)} pares`")

# Fila superior de métricas integrales
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🏦 Patrimonio Total Cuenta", f"${total_equity_display:,.2f} USDT")
c2.metric("💵 USDT Libre (Líquido)", f"${free_cash_display:,.2f} USDT")
c3.metric("🪙 En Criptos / Posiciones", f"${crypto_val_display:,.2f} USDT")
c4.metric("📦 Activos en Posesión", f"{len(active_crypto_assets)} monedas")
c5.metric("📋 Órdenes Abiertas Binance", f"{len(real_open_orders)} órdenes")

st.markdown("---")

# Pestañas principales
tab_radar, tab_portfolio, tab_analytics, tab_chart, tab_news, tab_binance_guide = st.tabs([
    "🎯 Radar de Oportunidades (< 30 min)",
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
        st.info(f"Escaneando **{len(selected_pairs_to_scan)} criptomonedas** en temporalidad **{tf_clean}** con datos en vivo de Binance (Modo: {sensitivity}).")
        
    if run_scan or "last_scan_results" not in st.session_state:
        with st.spinner(f"🤖 Escaneando {len(selected_pairs_to_scan)} criptomonedas simultáneamente en Binance..."):
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
                        
                # Plan de Trading Propuesto
                st.markdown("**🎯 Plan de Ejecución Sugerido por la IA:**")
                p1, p2, p3, p4 = st.columns(4)
                p1.markdown(f"<div class='trade-pill'>🟢 <b>Entrada:</b> ${opp['entry_price']:,.6f}</div>", unsafe_allow_html=True)
                p2.markdown(f"<div class='trade-pill' style='color:#f87171;'>🛑 <b>Stop Loss:</b> ${opp['stop_loss']:,.6f} (-{opp['sl_percent']}%)</div>", unsafe_allow_html=True)
                p3.markdown(f"<div class='trade-pill' style='color:#4ade80;'>🎯 <b>Take Profit:</b> ${opp['take_profit']:,.6f} (+{opp['tp_percent']}%)</div>", unsafe_allow_html=True)
                p4.markdown(f"<div class='trade-pill'>⚖️ <b>Ratio R:R:</b> 1:{opp['risk_reward_ratio']}</div>", unsafe_allow_html=True)
                
                # Formulario Personalizado de Entrada
                with st.expander(f"📝 Tomar Entrada / Personalizar Orden para {opp['symbol']}", expanded=False):
                    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
                    with f_col1:
                        custom_entry = st.number_input(f"Precio de Entrada (${opp['symbol']})", value=float(opp['price']), format="%.6f", key=f"in_p_{opp['symbol']}_{idx}")
                    with f_col2:
                        default_inv = min(10.0, float(free_cash_display)) if free_cash_display >= 5.0 else 10.0
                        custom_amount = st.number_input(f"Capital a Invertir (USDT)", min_value=1.0, value=float(default_inv), step=1.0, key=f"in_amt_{opp['symbol']}_{idx}")
                    with f_col3:
                        custom_sl = st.number_input(f"Stop Loss (SL)", value=float(opp['stop_loss']), format="%.6f", key=f"in_sl_{opp['symbol']}_{idx}")
                    with f_col4:
                        custom_tp = st.number_input(f"Take Profit (TP)", value=float(opp['take_profit']), format="%.6f", key=f"in_tp_{opp['symbol']}_{idx}")
                        
                    if trading_mode == "🟢 Cuenta Real de Binance" and binance_live.is_connected:
                        if st.button(f"⚡ COMPRAR Y ENVIAR ORDEN OCO A BINANCE ({opp['symbol']})", key=f"btn_live_{opp['symbol']}_{idx}", type="primary", use_container_width=True):
                            with st.spinner(f"Enviando orden de compra por ${custom_amount:.2f} USDT y orden OCO a Binance Spot..."):
                                exec_res = binance_live.execute_spot_buy_and_oco(
                                    symbol=opp["symbol"],
                                    usdt_amount=custom_amount,
                                    stop_loss_price=custom_sl,
                                    take_profit_price=custom_tp
                                )
                                if exec_res["status"] == "success":
                                    st.success(f"🎉 ¡Orden Real Ejecutada en Binance! Comprado a ${exec_res['entry_price']:,.6f}. Orden OCO colocada con éxito.")
                                    broker.open_buy_order(
                                        symbol=opp["symbol"],
                                        price=exec_res["entry_price"],
                                        quantity=exec_res["quantity"],
                                        stop_loss=custom_sl,
                                        take_profit=custom_tp,
                                        reason=f"Binance Real: {opp['setup_type']}"
                                    )
                                    st.rerun()
                                else:
                                    st.error(f"Error al enviar orden a Binance: {exec_res['message']}")
                    else:
                        if st.button(f"💾 Guardar Posición ({opp['symbol']})", key=f"btn_save_{opp['symbol']}_{idx}", type="primary", use_container_width=True):
                            qty = custom_amount / custom_entry
                            res = broker.open_buy_order(
                                symbol=opp["symbol"],
                                price=custom_entry,
                                quantity=qty,
                                stop_loss=custom_sl,
                                take_profit=custom_tp,
                                reason=f"{opp['setup_type']}"
                            )
                            if res["status"] == "executed":
                                st.success(f"¡Posición de {opp['symbol']} guardada por ${custom_amount:.2f} USDT! Monitoreándose en 'Mi Portafolio'.")
                                st.rerun()
                            else:
                                st.error(res["message"])
                st.markdown("---")

# =========================================================================
# TAB 2: MI PORTAFOLIO & ACTIVOS EN BINANCE (VALUACIÓN TOTAL)
# =========================================================================
with tab_portfolio:
    sub_t1, sub_t2, sub_t3, sub_t4 = st.tabs([
        "🪙 Mis Criptomonedas en Posesión",
        "📋 Órdenes Abiertas en Binance (OCO / Limit)",
        "🟢 Posiciones en Seguimiento Activo",
        "➕ Registrar Entrada Manual"
    ])
    
    # -------------------------------------------------------------
    # SUB-TAB 1: MIS CRIPTOMONEDAS EN POSESIÓN
    # -------------------------------------------------------------
    with sub_t1:
        st.subheader("🪙 Criptomonedas y Distribución Patrimonial")
        
        if active_crypto_assets:
            col_chart_pie, col_assets_list = st.columns([1, 2])
            with col_chart_pie:
                df_pie = pd.DataFrame(active_crypto_assets)
                fig_pie = go.Figure(data=[go.Pie(
                    labels=df_pie['asset'],
                    values=df_pie['value_usdt'],
                    hole=.4,
                    textinfo='label+percent',
                    marker=dict(colors=['#f0b90b', '#0ecb81', '#38bdf8', '#8b5cf6', '#f43f5e'])
                )])
                fig_pie.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#151a23", font={'color': "white"})
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with col_assets_list:
                for asset in active_crypto_assets:
                    st.markdown(f"""
                    <div class="card-opp" style="margin-bottom: 10px; padding: 14px; border-left: 6px solid #f0b90b;">
                        <div style="display:flex; justify-content: space-between; font-weight: bold; font-size: 17px;">
                            <span>🪙 {asset['asset']} ({asset['symbol']})</span>
                            <span style="color: #0ecb81;">${asset['value_usdt']:,.2f} USDT ({asset['percentage']}%)</span>
                        </div>
                        <div style="font-size: 13px; margin-top: 6px; color: #94a3b8;">
                            • Cantidad Total: <b>{asset['total_amount']:,.4f}</b> {asset['asset']}<br>
                            • En Órdenes de Venta (Bloqueado): <b>{asset['locked_in_orders']:,.4f}</b>  |  Libre: <b>{asset['free_amount']:,.4f}</b><br>
                            • Precio Unitario Actual: <b>${asset['unit_price_usdt']:,.6f} USDT</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No se detectaron criptomonedas en posesión o estás en 100% liquidez USDT. Si tienes SHIB o cualquier activo, verifica tus claves API en la barra lateral.")

    # -------------------------------------------------------------
    # SUB-TAB 2: ÓRDENES ABIERTAS EN BINANCE
    # -------------------------------------------------------------
    with sub_t2:
        st.subheader("📋 Órdenes de Venta / OCO Activas en Binance")
        if real_open_orders:
            st.success(f"🟢 Se detectaron **{len(real_open_orders)} órdenes activas** colocadas en tu cuenta de Binance:")
            df_open = pd.DataFrame(real_open_orders)[['symbol', 'type', 'side', 'price', 'stop_price', 'amount', 'total_usdt', 'datetime']]
            df_open.columns = ['Par', 'Tipo de Orden', 'Lado', 'Precio ($)', 'Stop Trigger ($)', 'Cantidad', 'Total ($ USDT)', 'Fecha / Hora']
            st.dataframe(df_open, use_container_width=True)
        else:
            st.info("No hay órdenes abiertas en este momento en tu cuenta de Binance.")

    # -------------------------------------------------------------
    # SUB-TAB 3: POSICIONES EN SEGUIMIENTO
    # -------------------------------------------------------------
    with sub_t3:
        st.subheader("🟢 Posiciones en Seguimiento Activo")
        
        current_prices = {}
        for pos_item in portfolio["open_positions"]:
            sym = pos_item["symbol"]
            t_data = tech_agent.fetch_ohlcv(symbol=sym, timeframe="5m", limit=2)
            if not t_data.empty:
                current_prices[sym] = float(t_data.iloc[-1]["close"])
                
        broker.update_and_check_positions(current_prices)
        portfolio_updated = broker.get_portfolio_summary(current_prices)
        
        if portfolio_updated["open_positions"]:
            for pos in portfolio_updated["open_positions"]:
                pnl_col = "#0ecb81" if pos["unrealized_pnl_usdt"] >= 0 else "#f6465d"
                with st.container():
                    st.markdown(f"""
                    <div class="card-opp" style="border-left: 6px solid {pnl_col};">
                        <div style="display:flex; justify-content: space-between; font-weight: bold; font-size: 18px;">
                            <span>{pos['symbol']} (Monto Invertido: ${pos['cost_usdt']:,.2f} USDT)</span>
                            <span style="color: {pnl_col};">${pos['unrealized_pnl_usdt']:+,.2f} ({pos['unrealized_pnl_pct']:+.2f}%)</span>
                        </div>
                        <div style="font-size: 14px; margin-top: 10px; color: #94a3b8;">
                            • Entrada: <b>${pos['entry_price']:,.4f}</b>  |  Precio Actual Binance: <b>${pos['current_price']:,.4f}</b><br>
                            • 🛑 <b>Stop Loss (SL):</b> <span style="color:#f87171;">${pos['stop_loss']:,.4f}</span>  |  
                            🎯 <b>Take Profit (TP):</b> <span style="color:#4ade80;">${pos['take_profit']:,.4f}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander(f"🔴 Registrar Salida / Cerrar Trade de {pos['symbol']}", expanded=True):
                        st.markdown(f"**Registra a qué precio vendiste en Binance para calcular tu ganancia/pérdida real:**")
                        c_exit1, c_exit2, c_exit3 = st.columns(3)
                        with c_exit1:
                            exit_p = st.number_input(f"Precio de Venta Real (${pos['symbol']})", value=float(pos['current_price']), format="%.6f", key=f"exit_p_{pos['symbol']}")
                        with c_exit2:
                            exit_r = st.selectbox("Motivo de Salida", ["TAKE_PROFIT (Ganancia)", "STOP_LOSS (Pérdida Cortada)", "CIERRE_MANUAL"], key=f"exit_r_{pos['symbol']}")
                        with c_exit3:
                            st.write("")
                            st.write("")
                            if st.button(f"✅ Confirmar Cierre de {pos['symbol']}", key=f"btn_close_{pos['symbol']}", type="primary", use_container_width=True):
                                res_close = broker.manual_close_position(pos['symbol'], exit_price=exit_p, exit_reason=exit_r)
                                if res_close["status"] == "success":
                                    st.success(f"¡Trade cerrado! PnL Realizado: ${res_close['trade']['pnl_usdt']:+,.2f} USDT ({res_close['trade']['pnl_percent']:+.2f}%)")
                                    st.rerun()
        else:
            st.info("No tienes posiciones activas en seguimiento en este momento.")

    # -------------------------------------------------------------
    # SUB-TAB 4: REGISTRAR ENTRADA MANUAL
    # -------------------------------------------------------------
    with sub_t4:
        st.subheader("➕ Registrar una Operación Manualmente")
        with st.form("manual_entry_form"):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                man_sym = st.selectbox("Criptomoneda", CATEGORIES["🌐 Top 50 Mercado Completo"], index=0)
                man_entry = st.number_input("Precio de Compra (Entrada en USDT)", min_value=0.000001, value=100.0, format="%.6f")
                man_amount_usdt = st.number_input("Monto Total Invertido (USDT)", min_value=1.0, value=10.0, step=1.0)
            with col_m2:
                man_sl = st.number_input("Stop Loss (SL en USDT)", min_value=0.000001, value=98.0, format="%.6f")
                man_tp = st.number_input("Take Profit (TP en USDT)", min_value=0.000001, value=104.0, format="%.6f")
                man_reason = st.text_input("Razón / Estrategia", value="Entrada en Binance según análisis de 5m")
                
            submit_manual = st.form_submit_button("💾 Guardar y Empezar Monitoreo", type="primary", use_container_width=True)
            if submit_manual:
                qty = man_amount_usdt / man_entry
                res = broker.open_buy_order(
                    symbol=man_sym,
                    price=man_entry,
                    quantity=qty,
                    stop_loss=man_sl,
                    take_profit=man_tp,
                    reason=man_reason
                )
                if res["status"] == "executed":
                    st.success(f"¡Posición de {man_sym} registrada por ${man_amount_usdt:.2f} USDT!")
                    st.rerun()
                else:
                    st.error(res["message"])

# =========================================================================
# TAB 3: MÉTRICAS & HISTORIAL DE DESEMPEÑO (ANALYTICS AVANZADO)
# =========================================================================
with tab_analytics:
    st.subheader("📈 Panel de Rendimiento y Estadísticas Históricas")
    
    trades = broker.trade_history
    
    if not trades:
        st.info("💡 Aún no tienes operaciones cerradas registradas. En cuanto tomes una entrada y la cierres (por Take Profit o Stop Loss), aquí verás tus curvas de rendimiento, Win Rate, factor de beneficio y análisis detallado.")
    else:
        winning_trades = [t for t in trades if t.get("pnl_usdt", 0) > 0]
        losing_trades = [t for t in trades if t.get("pnl_usdt", 0) <= 0]
        
        total_pnl = sum([t.get("pnl_usdt", 0) for t in trades])
        win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0.0
        
        gross_profit = sum([t.get("pnl_usdt", 0) for t in winning_trades])
        gross_loss = abs(sum([t.get("pnl_usdt", 0) for t in losing_trades]))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)
        
        avg_win = (gross_profit / len(winning_trades)) if winning_trades else 0.0
        avg_loss = (gross_loss / len(losing_trades)) if losing_trades else 0.0
        
        best_trade = max([t.get("pnl_usdt", 0) for t in trades])
        worst_trade = min([t.get("pnl_usdt", 0) for t in trades])
        
        # 1. Fila de Tarjetas de Rendimiento Clave
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("📦 Operaciones Cerradas", f"{len(trades)}")
        s2.metric("🟢 Trades Ganadores", f"{len(winning_trades)} ({win_rate:.1f}%)")
        s3.metric("🔴 Trades Perdedores", f"{len(losing_trades)}")
        s4.metric("💰 Ganancia Neta Total", f"${total_pnl:+,.2f} USDT")
        s5.metric("⚖️ Factor de Beneficio", f"{profit_factor:.2f}")
        
        s6, s7, s8, s9 = st.columns(4)
        s6.metric("🎯 Ganancia Promedio (Win)", f"+${avg_win:.2f} USDT")
        s7.metric("🛑 Pérdida Promedio (Loss)", f"-${avg_loss:.2f} USDT")
        s8.metric("🚀 Mejor Operación", f"+${best_trade:.2f} USDT")
        s9.metric("⚠️ Peor Operación", f"${worst_trade:.2f} USDT")
        
        st.markdown("---")
        
        # 2. Gráficos Visuales de Rendimiento (Curva de Capital + Donut de Aciertos)
        col_c1, col_c2 = st.columns([2, 1])
        
        with col_c1:
            st.subheader("📈 Curva de Crecimiento de Capital (Evolución PnL)")
            
            # Construir datos acumulados
            cum_pnl = np.cumsum([t.get("pnl_usdt", 0) for t in trades])
            trade_indices = [f"Trade #{i+1} ({t['symbol']})" for i, t in enumerate(trades)]
            
            fig_curve = go.Figure()
            fig_curve.add_trace(go.Scatter(
                x=trade_indices,
                y=cum_pnl,
                mode='lines+markers',
                line=dict(color='#0ecb81' if total_pnl >= 0 else '#f6465d', width=3),
                marker=dict(size=8, color='#f0b90b'),
                fill='tozeroy',
                fillcolor='rgba(14, 203, 129, 0.1)' if total_pnl >= 0 else 'rgba(246, 70, 93, 0.1)',
                name='PnL Acumulado'
            ))
            fig_curve.add_hline(y=0, line_dash="dash", line_color="gray")
            fig_curve.update_layout(
                height=280,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="#151a23",
                plot_bgcolor="#0e131b",
                font={'color': "#d1d4dc"}
            )
            st.plotly_chart(fig_curve, use_container_width=True)
            
        with col_c2:
            st.subheader("🎯 Proporción de Aciertos")
            fig_donut = go.Figure(data=[go.Pie(
                labels=['Ganadas (Wins)', 'Perdidas (Losses)'],
                values=[len(winning_trades), len(losing_trades)],
                hole=.5,
                marker=dict(colors=['#0ecb81', '#f6465d'])
            )])
            fig_donut.update_layout(
                height=280,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="#151a23",
                font={'color': "white"}
            )
            st.plotly_chart(fig_donut, use_container_width=True)
            
        st.markdown("---")
        
        # 3. Tabla Completa de Historial de Operaciones
        st.subheader("📜 Diario y Registro Detallado de Cada Trade")
        
        df_display = []
        for i, t in enumerate(trades):
            is_win = t.get("pnl_usdt", 0) > 0
            df_display.append({
                "#": i + 1,
                "Fecha / Hora": t.get("exit_time", "")[:16].replace("T", " "),
                "Criptomoneda": t.get("symbol", ""),
                "Entrada": f"${t.get('entry_price', 0):,.6f}",
                "Salida": f"${t.get('exit_price', 0):,.6f}",
                "Motivo de Cierre": t.get("exit_reason", ""),
                "Resultado PnL ($)": f"{'+' if is_win else ''}${t.get('pnl_usdt', 0):.4f} USDT",
                "Retorno (%)": f"{'+' if is_win else ''}{t.get('pnl_percent', 0):.2f}%",
                "Estrategia": t.get("signal_reason", "")
            })
            
        st.dataframe(pd.DataFrame(df_display), use_container_width=True)

# =========================================================================
# TAB 4: INSPECCIÓN DETALLADA DE GRÁFICO
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
# TAB 5: NOTICIAS & SENTIMIENTO GLOBAL
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
# TAB 6: GUÍA DE CONFIGURACIÓN PASO A PASO EN BINANCE
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
