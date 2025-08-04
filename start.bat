@echo off
echo Iniciando FuelTracker Pro...

:: Ativar ambiente virtual
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo ERRO: Ambiente virtual não encontrado. Execute setup.bat primeiro.
    pause
    exit /b 1
)

:: Verificar se .env existe
if not exist .env (
    echo ERRO: Arquivo .env não encontrado. Configure suas credenciais primeiro.
    echo Copiando exemplo...
    copy .env.example .env
    echo Configure o arquivo .env e execute novamente.
    pause
    exit /b 1
)

:: Inicializar banco de dados
echo Inicializando banco de dados...
py -c "from app import app, db; app.app_context().push(); db.create_all(); print('Banco criado com sucesso!')"

:: Iniciar aplicação
echo.
echo =================================
echo FuelTracker Pro iniciando...
echo =================================
echo.
echo Acesse: http://localhost:5000
echo Pressione Ctrl+C para parar
echo.

py app.py
