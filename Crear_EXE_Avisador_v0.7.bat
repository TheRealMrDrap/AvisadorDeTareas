@echo off
setlocal
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller pystray pillow
if errorlevel 1 goto :error
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "Avisador de Tareas v0.7" --icon "Mantenimiento.ico" --add-data "Mantenimiento.png;." --add-data "Mantenimiento.ico;." "AvisadorTareas_v0.7.py"
if errorlevel 1 goto :error
echo.
echo EXE creado en: dist\Avisador de Tareas v0.7.exe
echo El EXE es independiente y lleva los iconos integrados.
pause
exit /b 0
:error
echo ERROR al crear el EXE.
pause
exit /b 1
