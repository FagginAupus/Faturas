@echo off
cd /d "%~dp0"
echo Ativando ambiente virtual...
call venv\Scripts\activate.bat
echo Executando script de commit...
python commit.py
pause