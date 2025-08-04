#!/bin/bash

echo "🚗 Iniciando FuelTracker Pro..."

# Ativar ambiente virtual
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
else
    echo "❌ Ambiente virtual não encontrado. Execute ./setup.sh primeiro."
    exit 1
fi

# Verificar .env
if [ ! -f .env ]; then
    echo "❌ Arquivo .env não encontrado. Configure suas credenciais primeiro."
    cp .env.example .env
    echo "📝 Configure o arquivo .env e execute novamente."
    exit 1
fi

# Inicializar banco
echo "🗄️ Inicializando banco de dados..."
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('✅ Banco criado com sucesso!')"

echo ""
echo "🚀 FuelTracker Pro iniciando..."
echo "🌐 Acesse: http://localhost:5000"
echo "⏹️ Pressione Ctrl+C para parar"
echo ""

python app.py
