# 🤖 Sistema Multi-Agente de Trading & Análisis Cripto

Sistema modular con agentes de inteligencia artificial y análisis cuantitativo para operar en el mercado de criptomonedas con **Spot Trading**, órdenes **OCO (Stop-Loss & Take-Profit simultáneo)** y modo de **Paper Trading (Simulación)**.

---

## 🏗️ Arquitectura de Agentes

1. **Agente de Noticias & Sentimiento (`src/news/sentiment_agent.py`)**:
   - Rastrea en tiempo real el **Crypto Fear & Greed Index**.
   - Descarga y analiza titulares de **CoinTelegraph**, **CoinDesk** y **CryptoPanic**.
   - Clasifica y pondera noticias en *Bullish*, *Bearish* o *Neutral*.

2. **Agente de Análisis Técnico (`src/analysis/technical_agent.py`)**:
   - Conecta a Binance mediante CCXT para obtener velas OHLCV en vivo.
   - Calcula indicadores matemáticos: **EMAs (9, 20, 50, 200)**, **RSI (14)**, **MACD (12, 26, 9)**, **ATR (14)**, **Bandas de Bollinger**.
   - Detecta patrones de velas: *Bullish/Bearish Engulfing*, *Hammer*, *Shooting Star*, *Morning Star*, *Doji*.
   - Identifica soportes y resistencias dinámicos.

3. **Agente de Gestión de Riesgo (`src/risk/risk_manager.py`)**:
   - Calcula el tamaño de posición (*Position Sizing*) respetando el límite de riesgo (por defecto 1% de la cuenta por trade).
   - Fija el **Stop Loss** dinámico mediante ATR o soporte clave.
   - Fija el **Take Profit** garantizando un ratio Riesgo/Beneficio mínimo de **1:2**.
   - Activa el *Circuit Breaker* si la pérdida diaria alcanza el 3%.

4. **Motor de Ejecución & Paper Trading (`src/execution/paper_broker.py`)**:
   - Simula compras/ventas con comisiones reales de Binance Spot (0.1%).
   - Monitorea posiciones abiertas evaluando simultáneamente Stop Loss y Take Profit (lógica OCO).
   - Guarda el historial persistente en `paper_trading_state.json`.

5. **Cliente Binance Spot Real / Testnet (`src/execution/binance_client.py`)**:
   - Preparado para enviar órdenes OCO nativas a la API de Binance (`create_order_oco`) cuando se decida operar con micro-capital real.

---

## 🚀 Cómo Ejecutar el Sistema

### 1. Activar el entorno virtual (PowerShell)
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Ejecutar un escaneo único
```powershell
python main.py
```

### 3. Ejecutar en bucle continuo (ej. cada 60 segundos)
```powershell
python main.py --loop --interval 60
```

---

## ⚙️ Configuración (`.env`)

Copia `.env.example` a `.env` para personalizar tus parámetros:
```ini
TRADING_MODE=paper
INITIAL_PAPER_BALANCE=100.0
MAX_RISK_PER_TRADE_PERCENT=1.0
MAX_DAILY_LOSS_PERCENT=3.0
DEFAULT_TIMEFRAME=15m
TRADING_PAIRS=BTC/USDT,ETH/USDT,SOL/USDT
```
