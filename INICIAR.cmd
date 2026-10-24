@echo off
setlocal
cd /d "%~dp0"
set "FISCALIA_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%~dp0.venv\Scripts\python.exe" set "FISCALIA_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%FISCALIA_PY%" (
  echo No se encontro el Python preparado. Consulta README.md para instalar las dependencias en otro equipo.
  pause
  exit /b 1
)
echo Abre http://127.0.0.1:8765 en tu navegador.
echo Las cuentas estan en .data\CREDENCIALES_LOCALES.txt
echo Cierra con Ctrl+C o desde el boton Detener servidor del administrador.
"%FISCALIA_PY%" "%~dp0server.py"
pause
