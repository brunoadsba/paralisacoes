@echo off
cd /d "%~dp0.."
call .venv\Scripts\activate
pyinstaller --noconfirm --clean Paralisacoes.spec
if errorlevel 1 (
  echo.
  echo ERRO no build. Feche Paralisacoes.exe se estiver aberto e tente de novo.
  exit /b 1
)
echo.
echo Build concluido: dist\Paralisacoes\Paralisacoes.exe
