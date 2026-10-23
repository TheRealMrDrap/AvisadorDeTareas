@echo off
setlocal
cd /d "%~dp0"

echo Instalando o actualizando dependencias...
python -m pip install --upgrade pyinstaller pystray pillow
if errorlevel 1 goto :error

echo.
echo Creando EXE independiente con los iconos integrados...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "Avisador de Tareas" --icon "Mantenimiento.ico" --add-data "Mantenimiento.png;." --add-data "Mantenimiento.ico;." "AvisadorTareas_v0.6.py"
if errorlevel 1 goto :error

echo.
echo EXE creado correctamente:
echo %~dp0dist\Avisador de Tareas.exe
echo.
echo Ese EXE ya NO necesita Mantenimiento.png ni Mantenimiento.ico a su lado.
pause
exit /b 0

:error
echo.
echo ERROR: no se pudo crear el ejecutable.
pause
exit /b 1
