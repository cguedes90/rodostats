@echo off
echo Configurando FuelTracker Pro...

:: Verificar se Python está instalado
py --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python não encontrado. Instale Python 3.8+ primeiro.
    pause
    exit /b 1
)

:: Criar ambiente virtual
echo Criando ambiente virtual...
py -m venv venv

:: Ativar ambiente virtual
echo Ativando ambiente virtual...
call venv\Scripts\activate.bat

:: Atualizar pip
echo Atualizando pip...
py -m pip install --upgrade pip

:: Instalar dependências
echo Instalando dependências...
pip install -r requirements.txt

:: Verificar se .env existe
if not exist .env (
    echo Criando arquivo .env...
    copy .env.example .env
    echo.
    echo IMPORTANTE: Configure o arquivo .env com suas credenciais antes de executar a aplicação!
    echo.
)

:: Criar diretórios necessários
if not exist static\uploads mkdir static\uploads
if not exist static\icons mkdir static\icons

echo.
echo =================================
echo FuelTracker Pro configurado com sucesso!
echo =================================
echo.
echo Próximos passos:
echo 1. Configure o arquivo .env com suas credenciais
echo 2. Execute: start.bat
echo.
pause
