@echo off
cd /d "%~dp0"
echo.
echo ========================================
echo   DocumentBrain CHATBOT APP  (App 2)
echo   Open: http://localhost:8501
echo ========================================
echo.
python -m streamlit run chatbot_service/app.py --server.port 8501
pause
