@echo off
rem Lanzador del editor DISVIMAT.
rem Doble clic sobre este archivo, o ejecutarlo desde cualquier consola.
rem La primera vez crea el entorno de Python e instala las dependencias.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Preparando el entorno de Python por primera vez; puede tardar unos minutos...
    py -3 -m venv .venv
    if errorlevel 1 goto :error
    ".venv\Scripts\python.exe" -m pip install -e .[desktop]
    if errorlevel 1 goto :error
)

start "DISVIMAT" ".venv\Scripts\pythonw.exe" -m disvimat.desktop
exit /b 0

:error
echo.
echo No se pudo preparar el entorno.
echo Necesitas Python 3.12 o superior instalado desde https://www.python.org/
pause
exit /b 1
