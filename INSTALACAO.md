# 🚗 FuelTracker Pro - Instruções de Instalação

## ⚠️ Pré-requisitos Necessários

### 1. Instalar Python
**O Python não foi encontrado no seu sistema. Você precisa instalá-lo primeiro:**

1. **Baixe o Python 3.8+ do site oficial:**
   - Acesse: https://www.python.org/downloads/windows/
   - Baixe a versão mais recente (Python 3.11+ recomendado)

2. **Durante a instalação:**
   - ✅ **IMPORTANTE**: Marque "Add Python to PATH"
   - ✅ Marque "Install for all users" (opcional)
   - Execute como administrador

3. **Verificar instalação:**
   ```cmd
   python --version
   pip --version
   ```

### 2. Dependências Opcionais

#### Tesseract OCR (para IA de recibos)
1. **Baixe o Tesseract:**
   - https://github.com/UB-Mannheim/tesseract/wiki
   - Baixe a versão Windows (.exe)

2. **Instale em:**
   - `C:\Program Files\Tesseract-OCR\`
   - Adicione ao PATH se necessário

#### Google Chrome/Edge (para PWA)
- Necessário para testar a funcionalidade PWA

## 🚀 Instalação da Aplicação

### Depois de instalar o Python:

1. **Abra o PowerShell/CMD como Administrador**

2. **Navegue até a pasta:**
   ```cmd
   cd "C:\Users\usuario\Documents\Apps\Rodostats"
   ```

3. **Execute a configuração:**
   ```cmd
   setup.bat
   ```

4. **Configure suas credenciais:**
   - Edite o arquivo `.env`
   - Adicione suas chaves de API (opcional)

5. **Inicie a aplicação:**
   ```cmd
   start.bat
   ```

6. **Acesse no navegador:**
   - http://localhost:5000

## 🔑 Configuração das APIs (Opcional)

### Google Gemini AI (para processamento de recibos)
1. Acesse: https://makersuite.google.com/app/apikey
2. Crie uma chave de API gratuita
3. Adicione no `.env`: `GEMINI_API_KEY=sua-chave`

### SendGrid (para emails de boas-vindas)
1. Crie conta gratuita: https://sendgrid.com/
2. Gere uma API Key
3. Adicione no `.env`: `SENDGRID_API_KEY=sua-chave`

## 📱 Usando a Aplicação

### Recursos Principais:
- ✅ **Cadastro de veículos** (funciona sem APIs)
- ✅ **Registro manual de abastecimentos**
- ✅ **Dashboard com gráficos**
- ✅ **Histórico e análises**
- ✅ **PWA instalável**
- 🤖 **Processamento IA de recibos** (precisa Gemini API)
- 📧 **Emails automáticos** (precisa SendGrid)

### Primeiro Acesso:
1. Crie sua conta local
2. Cadastre um veículo
3. Registre um abastecimento
4. Explore o dashboard!

## 🔧 Solução de Problemas

### Python não encontrado:
- Reinstale o Python marcando "Add to PATH"
- Reinicie o terminal/computador

### Erro de permissões:
- Execute como administrador
- Verifique antivírus

### Banco de dados:
- A aplicação usa PostgreSQL na Neon
- Connection string já configurada
- Tabelas são criadas automaticamente

### PWA não instala:
- Use Chrome/Edge
- Acesse via HTTPS em produção
- Verifique console do navegador

## 📞 Suporte

Se precisar de ajuda:
1. Verifique se seguiu todos os passos
2. Consulte os logs no terminal
3. Abra uma issue no GitHub

**Desenvolvido com ❤️ por InovaMente Labs**
