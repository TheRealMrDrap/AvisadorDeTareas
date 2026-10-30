@echo off
setlocal
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller pystray pillow
if errorlevel 1 goto :error
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "Avisador de Tareas v0.9.5" --icon "Mantenimiento.ico" --add-data "AvisadorTareas_Icono_512.png;." --add-data "Mantenimiento.ico;." "AvisadorTareas_v0.9.5.py"
if errorlevel 1 goto :error
echo EXE creado en dist\Avisador de Tareas v0.9.5.exe
pause
exit /b 0
:error
echo ERROR al crear el EXE.
pause
exit /b 1
