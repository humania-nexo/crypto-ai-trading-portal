@echo off
title Crypto AI Trading Portal
echo ===================================================
echo     INICIANDO PORTAL WEB DE TRADING CRIPTO AI
echo ===================================================
echo.
call .\venv\Scripts\activate.bat
streamlit run app.py
pause
