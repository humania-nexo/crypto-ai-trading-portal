"""
Crypto Multi-Agent Web Portal & AI Opportunity Radar with Complete Trading Journal.
Built with Streamlit & Plotly.
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime
from dotenv import load_dotenv

import importlib
import src.analysis.market_scanner
import src.execution.paper_broker
import src.analysis.technical_agent
import src.analysis.patterns
import src.risk.risk_manager

importlib.reload(src.analysis.market_scanner)
importlib.reload(src.execution.paper_broker)
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

load_dotenv()

# Configuración de página
st.set_page_config(
    page_title="Crypto AI - Radar de Oportunidades",
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
</style>
""", unsafe_allow_html=True)

# Inicializar agentes
def get_agents():
    tech = TechnicalAgent(exchange_id="binance")
    sentiment = SentimentAgent(cryptopanic_api_key=os.getenv("CRYPTOPANIC_API_KEY"))
    broker = PaperBroker(initial_balance=100.0, state_file="paper_trading_state.json")
    risk = RiskManager(max_risk_per_trade_pct=1.0, max_daily_loss_pct=3.0, min_risk_reward_ratio=2.0)
    risk.set_daily_baseline(broker.balance_usdt)
    scanner = MarketScanner(tech, sentiment, risk)
    return tech, sentiment, risk, broker, scanner

tech_agent, sentiment_agent, risk_manager, broker, scanner = get_agents()

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("## 🪙 **Crypto AI Radar**")
    st.caption("Asistente Autónomo de Análisis & Diario de Trading")
    
    st.subheader("💵 Configurar Saldo de Cuenta")
    user_bal = st.number_input("Saldo en USDT", min_value=1.0, max_value=1000000.0, value=float(broker.balance_usdt), step=5.0)
    if user_bal != broker.balance_usdt:
        if st.button("💾 Actualizar Saldo", use_container_width=True):
            broker.balance_usdt = round(float(user_bal), 2)
            if hasattr(broker, 'set_custom_balance'):
                broker.set_custom_balance(user_bal)
            else:
                broker.save_state()
            risk_manager.set_daily_baseline(user_bal)
            st.success(f"Saldo actualizado a ${user_bal:,.2f} USDT")
            st.rerun()

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
    
    st.markdown("---")
    if st.button("🗑️ Reset Historial y Posiciones", use_container_width=True):
        broker.open_positions = {}
        broker.trade_history = []
        broker.save_state()
        st.success("Historial reiniciado correctamente.")
        st.rerun()

# --- HEADER Y MÉTRICAS DE CAPITAL ---
portfolio = broker.get_portfolio_summary()

st.title("🎯 Radar de Oportunidades & Diario de Trading Real")
st.markdown("La IA escanea decenas de criptomonedas en paralelo, analiza velas, indicadores y figuras chartistas, y te permite **registrar y monitorear cada entrada con sus métricas exactas**.")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💰 Balance Libre", f"${portfolio['cash_balance_usdt']:,.2f} USDT")
c2.metric("🏦 Patrimonio Total", f"${portfolio['total_equity_usdt']:,.2f} USDT")
c3.metric("📈 PnL No Realizado", f"${portfolio['unrealized_pnl_usdt']:+,.2f} USDT")
c4.metric("🟢 Posiciones Activas", f"{portfolio['open_positions_count']}")
c5.metric("🏆 Win Rate Histórico", f"{portfolio['win_rate']:.1f}% ({portfolio['total_trades']} cerradas)")

st.markdown("---")

# Pestañas principales
tab_radar, tab_portfolio, tab_chart, tab_news, tab_binance_guide = st.tabs([
    "🎯 Radar de Oportunidades (< 30 min)",
    "💼 Mi Portafolio & Diario de Trading",
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
        st.warning("⏳ En este momento ningún par cumple con los filtros de confluencia alcista en temporalidad 5m. La IA recomienda mantenerse en liquidez (USDT).")
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
                            <span style="font-size: 16px; color: #848e9c; margin-left: 10px;">Precio Actual: <b>${opp['price']:,.4f}</b></span>
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
                p1.markdown(f"<div class='trade-pill'>🟢 <b>Entrada:</b> ${opp['entry_price']:,.4f}</div>", unsafe_allow_html=True)
                p2.markdown(f"<div class='trade-pill' style='color:#f87171;'>🛑 <b>Stop Loss:</b> ${opp['stop_loss']:,.4f} (-{opp['sl_percent']}%)</div>", unsafe_allow_html=True)
                p3.markdown(f"<div class='trade-pill' style='color:#4ade80;'>🎯 <b>Take Profit:</b> ${opp['take_profit']:,.4f} (+{opp['tp_percent']}%)</div>", unsafe_allow_html=True)
                p4.markdown(f"<div class='trade-pill'>⚖️ <b>Ratio R:R:</b> 1:{opp['risk_reward_ratio']}</div>", unsafe_allow_html=True)
                
                # Formulario Personalizado de Entrada para el Usuario
                with st.expander(f"📝 Tomar Entrada / Personalizar Datos para {opp['symbol']}", expanded=False):
                    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
                    with f_col1:
                        custom_entry = st.number_input(f"Precio de Entrada (${opp['symbol']})", value=float(opp['price']), format="%.6f", key=f"in_p_{opp['symbol']}_{idx}")
                    with f_col2:
                        custom_amount = st.number_input(f"Capital a Invertir (USDT)", min_value=1.0, value=min(10.0, float(portfolio['cash_balance_usdt'])), step=1.0, key=f"in_amt_{opp['symbol']}_{idx}")
                    with f_col3:
                        custom_sl = st.number_input(f"Stop Loss (SL)", value=float(opp['stop_loss']), format="%.6f", key=f"in_sl_{opp['symbol']}_{idx}")
                    with f_col4:
                        custom_tp = st.number_input(f"Take Profit (TP)", value=float(opp['take_profit']), format="%.6f", key=f"in_tp_{opp['symbol']}_{idx}")
                        
                    if st.button(f"💾 Guardar y Monitorear Posición de {opp['symbol']}", key=f"btn_save_{opp['symbol']}_{idx}", type="primary", use_container_width=True):
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
                            st.success(f"¡Excelente! Posición de {opp['symbol']} guardada por ${custom_amount:.2f} USDT. La puedes seguir en 'Mi Portafolio'.")
                            st.rerun()
                        else:
                            st.error(res["message"])
                st.markdown("---")

# =========================================================================
# TAB 2: MI PORTAFOLIO & DIARIO DE TRADING REAL
# =========================================================================
with tab_portfolio:
    sub_t1, sub_t2, sub_t3 = st.tabs([
        "🟢 Posiciones Activas en Monitoreo",
        "➕ Registrar Entrada Manual (Cualquier Moneda)",
        "📊 Estadísticas & Historial Completo"
    ])
    
    # -------------------------------------------------------------
    # SUB-TAB 1: POSICIONES ACTIVAS
    # -------------------------------------------------------------
    with sub_t1:
        st.subheader("🟢 Posiciones Abiertas (Monitoreo en Tiempo Real)")
        
        # Actualizar precios en vivo
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
            st.info("No tienes posiciones activas en este momento. Escanea el mercado en la pestaña 1 o registra una entrada manual abajo.")

    # -------------------------------------------------------------
    # SUB-TAB 2: REGISTRAR ENTRADA MANUAL
    # -------------------------------------------------------------
    with sub_t2:
        st.subheader("➕ Registrar una Operación Tomada en Binance")
        st.caption("Si compraste cualquier criptomoneda directamente en Binance, ingresa aquí los datos exactos para llevar el seguimiento:")
        
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
                    st.success(f"¡Posición de {man_sym} registrada por ${man_amount_usdt:.2f} USDT! Monitoreándose activamente.")
                    st.rerun()
                else:
                    st.error(res["message"])

    # -------------------------------------------------------------
    # SUB-TAB 3: ESTADÍSTICAS & HISTORIAL
    # -------------------------------------------------------------
    with sub_t3:
        st.subheader("📊 Métricas de Desempeño & Historial de Trades")
        
        st1, st2, st3, st4, st5 = st.columns(5)
        st1.metric("Total Operaciones", f"{portfolio['total_trades']}")
        st2.metric("Ganadas (Wins)", f"{portfolio.get('winning_trades', 0)} 🟢")
        st3.metric("Perdidas (Losses)", f"{portfolio.get('losing_trades', 0)} 🔴")
        st4.metric("Tasa de Acierto", f"{portfolio['win_rate']:.1f}%")
        st5.metric("PnL Realizado Total", f"${portfolio['total_realized_pnl_usdt']:+,.2f} USDT")
        
        st.markdown("---")
        st.subheader("📜 Tabla del Historial de Operaciones Cerradas")
        if broker.trade_history:
            df_hist = pd.DataFrame(broker.trade_history)[['symbol', 'entry_price', 'exit_price', 'exit_reason', 'pnl_usdt', 'pnl_percent', 'entry_time', 'exit_time', 'signal_reason']]
            st.dataframe(df_hist, use_container_width=True)
        else:
            st.info("El historial de operaciones cerradas está vacío. Cuando cierres tu primera operación, aparecerán aquí todas tus estadísticas.")

# =========================================================================
# TAB 3: INSPECCIÓN DETALLADA DE GRÁFICO
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
# TAB 4: NOTICIAS & SENTIMIENTO GLOBAL
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
# TAB 5: GUÍA DE CONFIGURACIÓN PASO A PASO EN BINANCE
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
