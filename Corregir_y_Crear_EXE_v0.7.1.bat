@echo off
setlocal
cd /d "%~dp0"
python "Corregir_v0.7_a_v0.7.1.py"
if errorlevel 1 goto :error
python -m py_compile "AvisadorTareas_v0.7.1.py"
if errorlevel 1 goto :error
python -m pip install --upgrade pyinstaller pystray pillow
if errorlevel 1 goto :error
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "Avisador de Tareas v0.7.1" --icon "Mantenimiento.ico" --add-data "Mantenimiento.png;." --add-data "Mantenimiento.ico;." "AvisadorTareas_v0.7.1.py"
if errorlevel 1 goto :error
echo.
echo CORRECTO: dist\Avisador de Tareas v0.7.1.exe
pause
exit /b 0
:error
echo.
echo ERROR: revisa el mensaje mostrado arriba.
pause
exit /b 1
