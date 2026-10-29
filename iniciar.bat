@echo off
REM Painel Tributario - inicia no Windows (duplo clique).
cd /d "%~dp0"
if not exist .venv (
  echo Criando ambiente Python...
  python -m venv .venv || (echo Instale o Python 3.10+ em python.org e marque "Add to PATH". & pause & exit /b 1)
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip >nul
  pip install -r requirements.txt || (pause & exit /b 1)
) else (
  call .venv\Scripts\activate.bat
)
python run.py
pause
