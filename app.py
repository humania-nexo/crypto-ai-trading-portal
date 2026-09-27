"""
Crypto Multi-Agent Web Portal & Interactive Trading Dashboard.
Built with Streamlit & Plotly.
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import json
from datetime import datetime
from dotenv import load_dotenv

from src.news.sentiment_agent import SentimentAgent
from src.analysis.technical_agent import TechnicalAgent
from src.analysis.indicators import TechnicalIndicators
from src.analysis.patterns import PatternDetector
from src.risk.risk_manager import RiskManager
from src.execution.paper_broker import PaperBroker
from src.strategies.strategy_synthesizer import StrategySynthesizer

load_dotenv()

# Configuración de página
st.set_page_config(
    page_title="Crypto AI Trading Portal",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo personalizado CSS moderno oscuro
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #2a2e39; }
    .card { background-color: #1e222d; padding: 20px; border-radius: 10px; border: 1px solid #2a2e39; margin-bottom: 20px; }
    .badge-bullish { background-color: #0ecb81; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-bearish { background-color: #f6465d; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-neutral { background-color: #707a8a; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# Inicializar sesión de agentes
@st.cache_resource
def get_agents():
    tech = TechnicalAgent(exchange_id="binance")
    sentiment = SentimentAgent(cryptopanic_api_key=os.getenv("CRYPTOPANIC_API_KEY"))
    broker = PaperBroker(initial_balance=100.0, state_file="paper_trading_state.json")
    risk = RiskManager(max_risk_per_trade_pct=1.0, max_daily_loss_pct=3.0, min_risk_reward_ratio=2.0)
    risk.set_daily_baseline(broker.balance_usdt)
    synthesizer = StrategySynthesizer(tech, sentiment, risk, broker)
    return tech, sentiment, risk, broker, synthesizer

tech_agent, sentiment_agent, risk_manager, broker, synthesizer = get_agents()

# --- BARRA LATERAL (CONFIGURACIÓN) ---
with st.sidebar:
    st.image("https://cryptologos.cc/logos/binance-coin-bnb-logo.png", width=50)
    st.title("Panel de Control")
    
    st.subheader("⚙️ Parámetros de Operación")
    trading_mode = st.selectbox("Modo de Trading", ["Paper Trading (Simulador)", "Binance Testnet", "Binance Spot Real (Micro)"], index=0)
    selected_pair = st.selectbox("Par Cripto", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "ADA/USDT", "XRP/USDT"], index=0)
    timeframe = st.selectbox("Temporalidad Velas", ["5m", "15m", "1h", "4h", "1d"], index=1)
    
    st.subheader("🛡️ Gestión de Riesgo")
    risk_pct = st.slider("Riesgo Máximo por Trade (%)", min_value=0.5, max_value=3.0, value=1.0, step=0.1)
    risk_manager.max_risk_per_trade_pct = risk_pct
    
    max_daily_loss = st.slider("Límite Pérdida Diaria (%)", min_value=1.0, max_value=5.0, value=3.0, step=0.5)
    risk_manager.max_daily_loss_pct = max_daily_loss
    
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        scan_now = st.button("🔄 Escanear", use_container_width=True)
    with col_btn2:
        if st.button("🗑️ Reset Saldo", use_container_width=True):
            broker.balance_usdt = 100.0
            broker.open_positions = {}
            broker.trade_history = []
            broker.save_state()
            st.success("Portafolio reiniciado a $100 USDT")
            st.rerun()

# --- HEADER PRINCIPAL & MÉTRICAS ---
st.title("🤖 Portal Multi-Agente de Trading & Análisis Cripto")
st.caption(f"Conectado a Binance Spot | Temporalidad: {timeframe} | Modo: {trading_mode}")

# Actualizar datos de mercado
df_raw = tech_agent.fetch_ohlcv(symbol=selected_pair, timeframe=timeframe, limit=120)
if not df_raw.empty:
    df_ind = TechnicalIndicators.calculate_all(df_raw)
    signals = TechnicalIndicators.get_latest_signal_summary(df_ind)
    current_price = signals.get("close", 0.0)
else:
    current_price = 0.0
    signals = {}
    df_ind = pd.DataFrame()

# Actualizar OCO en broker
closed_trades = broker.update_and_check_positions({selected_pair: current_price})
portfolio = broker.get_portfolio_summary({selected_pair: current_price})

# Fila de métricas clave
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("💰 Balance Disponible", f"${portfolio['cash_balance_usdt']:,.2f} USDT")
m2.metric("🏦 Patrimonio Total", f"${portfolio['total_equity_usdt']:,.2f} USDT")
m3.metric("📈 PnL No Realizado", f"${portfolio['unrealized_pnl_usdt']:+,.2f} USDT")
m4.metric("🏆 Win Rate", f"{portfolio['win_rate']:.1f}%")
m5.metric("📦 Operaciones Totales", f"{portfolio['total_trades']}")

st.markdown("---")

# --- SECCIÓN 1: SENTIMIENTO & NOTICIAS ---
col_sent, col_news = st.columns([1, 2])

with col_sent:
    st.subheader("🧭 Sentimiento del Mercado")
    sent_data = sentiment_agent.get_market_sentiment_summary()
    fng = sent_data["fear_and_greed"]
    
    # Indicador tipo Gauge con Plotly
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
    fig_gauge.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="#1e222d", font={'color': "white"})
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_news:
    st.subheader("📰 Titulares & Noticias en Vivo")
    for news_item in sent_data.get("recent_headlines", [])[:4]:
        badge_class = "badge-bullish" if news_item["sentiment"] == "BULLISH" else ("badge-bearish" if news_item["sentiment"] == "BEARISH" else "badge-neutral")
        st.markdown(f"""
        <div style="background-color: #1e222d; padding: 10px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #2a2e39;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 11px; color: #848e9c;">{news_item['source']} • {news_item.get('published', '')[:16]}</span>
                <span class="{badge_class}">{news_item['sentiment']}</span>
            </div>
            <div style="font-weight: 500; font-size: 13px; margin-top: 4px;">
                <a href="{news_item['link']}" target="_blank" style="color: #eaecef; text-decoration: none;">{news_item['title']}</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# --- SECCIÓN 2: GRÁFICO INTERACTIVO & ANÁLISIS TÉCNICO ---
st.subheader(f"📊 Gráfico de Precios e Indicadores: {selected_pair} ({timeframe})")

if not df_ind.empty:
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2]
    )
    
    # 1. Velas Japonesas
    fig.add_trace(go.Candlestick(
        x=df_ind['datetime'],
        open=df_ind['open'],
        high=df_ind['high'],
        low=df_ind['low'],
        close=df_ind['close'],
        name='Precio'
    ), row=1, col=1)
    
    # EMAs
    fig.add_trace(go.Scatter(x=df_ind['datetime'], y=df_ind['ema_20'], line=dict(color='#f0b90b', width=1.5), name='EMA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_ind['datetime'], y=df_ind['ema_50'], line=dict(color='#0ecb81', width=1.5), name='EMA 50'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_ind['datetime'], y=df_ind['ema_200'], line=dict(color='#8b5cf6', width=2), name='EMA 200'), row=1, col=1)
    
    # Bollinger Bands
    fig.add_trace(go.Scatter(x=df_ind['datetime'], y=df_ind['bb_upper'], line=dict(color='rgba(255,255,255,0.2)', dash='dot'), name='BB Superior'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_ind['datetime'], y=df_ind['bb_lower'], line=dict(color='rgba(255,255,255,0.2)', dash='dot'), fill='tonexty', fillcolor='rgba(255,255,255,0.03)', name='BB Inferior'), row=1, col=1)
    
    # 2. RSI
    fig.add_trace(go.Scatter(x=df_ind['datetime'], y=df_ind['rsi'], line=dict(color='#3b82f6', width=1.5), name='RSI (14)'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", line_width=1, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", line_width=1, row=2, col=1)
    
    # 3. MACD
    fig.add_trace(go.Scatter(x=df_ind['datetime'], y=df_ind['macd'], line=dict(color='#0ecb81', width=1.5), name='MACD'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_ind['datetime'], y=df_ind['macd_signal'], line=dict(color='#f6465d', width=1.5), name='Signal'), row=3, col=1)
    fig.add_trace(go.Bar(x=df_ind['datetime'], y=df_ind['macd_hist'], marker_color=['#0ecb81' if v >= 0 else '#f6465d' for v in df_ind['macd_hist']], name='Hist'), row=3, col=1)
    
    fig.update_layout(
        height=650,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_rangeslider_visible=False,
        paper_bgcolor="#1e222d",
        plot_bgcolor="#131722",
        font={'color': "#d1d4dc"}
    )
    st.plotly_chart(fig, use_container_width=True)

# --- SECCIÓN 3: DECISIÓN DEL ESTRATEGA & GATILLO DE ORDEN ---
col_dec1, col_dec2 = st.columns(2)

with col_dec1:
    st.subheader("🧠 Evaluación del Agente Estratega")
    if st.button(f"🎯 Ejecutar Análisis y Decisión para {selected_pair}", use_container_width=True) or scan_now:
        decision = synthesizer.evaluate_market_and_execute(selected_pair, timeframe=timeframe)
        st.json(decision)
        if decision.get("action") == "BUY_EXECUTED":
            st.success(f"¡Orden ejecutada con éxito! Entrada: ${decision['current_price']:,.2f}")
            st.rerun()

with col_dec2:
    st.subheader("🔍 Señales Cuantitativas Detectadas")
    patterns = PatternDetector.identify_candlestick_patterns(df_ind) if not df_ind.empty else []
    levels = PatternDetector.calculate_support_resistance(df_ind) if not df_ind.empty else {}
    
    st.write(f"• **Precio:** ${current_price:,.2f}")
    st.write(f"• **Tendencia:** {signals.get('trend', 'N/A')}")
    st.write(f"• **RSI (14):** {signals.get('rsi', 'N/A')} ({signals.get('rsi_condition', 'N/A')})")
    st.write(f"• **Soporte Clave:** ${levels.get('nearest_support', 0):,.2f} | **Resistencia:** ${levels.get('nearest_resistance', 0):,.2f}")
    
    if patterns:
        for p in patterns:
            st.info(f"**Patrón:** {p['pattern']} ({p['bias']}) - {p['description']}")
    else:
        st.write("• **Patrones de Velas:** Sin patrón significativo en velas recientes.")

st.markdown("---")

# --- SECCIÓN 4: POSICIONES ABIERTAS & HISTORIAL (OCO) ---
col_pos, col_hist = st.columns(2)

with col_pos:
    st.subheader("🟢 Posiciones Abiertas (OCO Activo)")
    if portfolio["open_positions"]:
        for pos in portfolio["open_positions"]:
            pnl_col = "#0ecb81" if pos["unrealized_pnl_usdt"] >= 0 else "#f6465d"
            st.markdown(f"""
            <div style="background-color: #1e222d; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39; margin-bottom: 10px;">
                <div style="display:flex; justify-content: space-between; font-weight: bold; font-size: 16px;">
                    <span>{pos['symbol']}</span>
                    <span style="color: {pnl_col};">${pos['unrealized_pnl_usdt']:+,.2f} ({pos['unrealized_pnl_pct']:+.2f}%)</span>
                </div>
                <div style="font-size: 13px; margin-top: 8px; color: #848e9c;">
                    Entrada: <b>${pos['entry_price']:,.2f}</b> | Actual: <b>${pos['current_price']:,.2f}</b><br>
                    🛑 Stop Loss (SL): <b style="color: #f6465d;">${pos['stop_loss']:,.2f}</b><br>
                    🎯 Take Profit (TP): <b style="color: #0ecb81;">${pos['take_profit']:,.2f}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No hay posiciones abiertas actualmente.")

with col_hist:
    st.subheader("📜 Historial de Operaciones Cerradas")
    if broker.trade_history:
        hist_df = pd.DataFrame(broker.trade_history)[['symbol', 'entry_price', 'exit_price', 'exit_reason', 'pnl_usdt', 'pnl_percent']]
        st.dataframe(hist_df.tail(6), use_container_width=True)
    else:
        st.info("El historial de operaciones está vacío.")
