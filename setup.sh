#!/bin/bash

echo "🚗 FuelTracker Pro - Setup Completo"
echo "=================================="

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Instale Python 3.8+ primeiro."
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"

# Criar ambiente virtual
echo "📦 Criando ambiente virtual..."
python3 -m venv venv

# Ativar ambiente virtual
echo "🔄 Ativando ambiente virtual..."
source venv/bin/activate

# Atualizar pip
echo "⬆️ Atualizando pip..."
pip install --upgrade pip

# Instalar dependências
echo "📚 Instalando dependências..."
pip install -r requirements.txt

# Configurar .env
if [ ! -f .env ]; then
    echo "⚙️ Criando arquivo .env..."
    cp .env.example .env
    echo "📝 Configure o arquivo .env com suas credenciais!"
fi

# Criar diretórios
mkdir -p static/uploads
mkdir -p static/icons

echo ""
echo "🎉 FuelTracker Pro configurado com sucesso!"
echo ""
echo "📋 Próximos passos:"
echo "1. Configure o arquivo .env"
echo "2. Execute: ./start.sh"
echo ""
