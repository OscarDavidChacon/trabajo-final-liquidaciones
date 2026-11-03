@echo off
setlocal
cd /d "%~dp0"

rem --- 1) Verificar uv (instalar si falta) ---
where uv >nul 2>nul
if errorlevel 1 (
  echo uv no encontrado. Instalando uv...
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
)

rem --- 2) Abrir el navegador unos segundos despues de arrancar el servidor ---
start "" cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:5000"

rem --- 3) Arrancar la app.
rem     Se usa "python -m flask" en lugar de "flask" porque el Control de
rem     aplicaciones de Windows bloquea el lanzador flask.exe (no firmado),
rem     mientras que python.exe si esta permitido. Es equivalente.
uv run python -m flask --app wsgi run --port 5000

endlocal
