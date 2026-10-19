@echo off
cd /d "%~dp0"
set "BUNDLED_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED_PY%" (
  "%BUNDLED_PY%" app.py
  if errorlevel 1 goto fallo
  exit /b 0
)
where python >nul 2>nul
if %errorlevel%==0 (
  python app.py
  if errorlevel 1 goto fallo
  exit /b 0
)
echo No se encontro Python. Instala Python 3.10+ para abrir la ventana del modelo.
:fallo
pause
exit /b 1

