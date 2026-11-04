@echo off
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo Install uv using the link in README.md, then run this launcher again.
  pause
  exit /b 1
)
uv sync --locked
if errorlevel 1 exit /b 1
uv run streamlit run app.py --server.port 8535
