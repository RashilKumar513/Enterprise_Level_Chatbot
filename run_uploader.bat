@echo off
cd /d "%~dp0"
echo.
echo ========================================
echo   DocumentBrain UPLOAD APP  (App 1)
echo   Open: http://127.0.0.1:8000
echo ========================================
echo.
python -m uvicorn uploader_service.main:app --host 127.0.0.1 --port 8000 --reload
pause
