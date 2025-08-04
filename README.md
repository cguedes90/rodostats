# 🚗 Rodo Stats - Controle Inteligente de Combustível

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/YOUR_USERNAME/rodostats)

## � Sobre o Projeto

O **Rodo Stats** é uma aplicação web moderna para controle inteligente de combustível, desenvolvida com Flask e integração com IA do Google Gemini. Permite aos usuários gerenciar múltiplos veículos, registrar abastecimentos, processar notas fiscais automaticamente e obter análises detalhadas de consumo.

## ✨ Funcionalidades Principais

### 🔐 Sistema de Autenticação
- **Registro e Login**: Sistema completo com email e senha
- **Sessões Seguras**: Gerenciamento seguro de sessões de usuário

### 🚙 Gestão de Veículos
- Cadastro ilimitado de veículos
- Validação de placa brasileira (ABC-1234 ou ABC1D23)
- Filtros específicos por veículo

### ⛽ Registro de Abastecimentos
- **Manual**: Litros, valor, tipo de combustível, quilometragem
- **Automático**: Upload de foto → OCR + Gemini AI → preenchimento automático
- Cálculos em tempo real (preço por litro)

### 📊 Dashboard Avançado
- Filtros inteligentes: 7 dias, 30 dias, 1 ano, todos os dados
- Métricas de gastos: Total gasto, litros, preço médio, posto favorito
- **Análise de Quilometragem e Consumo**:
  - Total de km rodados
  - Consumo médio (km/L) ponderado
  - Melhor e pior rendimento
  - Km rodados nos últimos 30 dias
  - Filtros inteligentes (remove dados irreais)

### 📈 Gráficos e Visualizações
- Gastos mensais (gráfico de barras)
- Distribuição de combustível (donut chart)
- Tendência de preços por litro
- Quebra por veículo

### 📋 Histórico e Edição
- Tabela completa de abastecimentos
- Edição inline de quilometragem (AJAX)
- Filtros aplicados respeitam seleções

### 👤 Perfil do Usuário
- Upload de foto personalizada com preview
- Dados pessoais e estatísticas
- Priorização: foto personalizada > OAuth

### 📤 Exportação de Dados
- **CSV**: Dados completos compatíveis com Excel/Sheets
- **PDF**: Layout profissional com gráficos (em desenvolvimento)

### 📱 Progressive Web App (PWA)
- Instalável no iOS e Android
- Ícones personalizados
- Service Worker para funcionalidade offline

## 🔧 Tecnologias Utilizadas

### Backend
- **Flask** (Python) - Framework web
- **PostgreSQL** - Banco de dados (Neon)
- **SQLAlchemy** - ORM
- **Google Gemini AI** - Processamento de recibos
- **SendGrid** - Envio de emails
- **Tesseract OCR** - Extração de texto de imagens
- **Pillow** - Processamento de imagens

### Frontend
- **Jinja2** - Templates
- **Bootstrap 5** - UI Framework (Dark Theme)
- **Chart.js** - Gráficos interativos
- **FontAwesome** - Ícones
- **JavaScript Vanilla** - Interatividade

### Integrações
- **Google Gemini AI**: Modelo gemini-2.0-flash-exp
- **SendGrid**: Templates HTML profissionais
- **PostgreSQL**: Banco robusto na Neon

## 📊 Modelos de Dados

```python
User: ID, email, nome, fotos (OAuth + personalizada), senha hash, provider
Vehicle: Marca, modelo, ano, placa, cor vinculados ao usuário  
FuelRecord: Litros, valor, tipo, quilometragem, posto, tanque, datas
```

## 🚀 Instalação e Configuração

### 1. Requisitos
- Python 3.8+
- PostgreSQL (ou conta Neon)
- Tesseract OCR (opcional)

### 2. Instalação
```bash
# Clone o repositório
git clone https://github.com/seu-usuario/rodostats.git
cd rodostats

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

### 3. Configuração do .env
```env
# Obrigatório
DATABASE_URL=sua-connection-string-neon
SESSION_SECRET=sua-chave-secreta-forte

# Opcional - IA e Email
GEMINI_API_KEY=sua-chave-google-gemini
SENDGRID_API_KEY=sua-chave-sendgrid

# OAuth (opcional)
GOOGLE_OAUTH_CLIENT_ID=seu-client-id
GOOGLE_OAUTH_CLIENT_SECRET=seu-client-secret
```

### 4. Executar a aplicação
```bash
# Desenvolvimento
python app.py

# Produção
gunicorn app:app
```

## 🔒 Segurança

- CSRF Protection
- SQL Injection prevention
- XSS prevention
- File upload validation
- Password hashing seguro (Werkzeug)

## 📈 Performance

- Database indexing
- Query optimization
- Connection pooling
- Session caching
- Asset minification
- Lazy loading

## 🌟 Diferenciais Competitivos

1. **IA Integrada**: Processamento automático de recibos brasileiros
2. **Análise Inteligente**: Métricas precisas de consumo com filtros
3. **PWA Moderna**: Experiência mobile nativa
4. **Interface Profissional**: Dark theme com feedback em tempo real
5. **Gratuito**: 100% gratuito com recursos ilimitados

## 🔄 Fluxos de Trabalho

### Registro Manual
1. Formulário → validação → cálculo automático → salvamento

### Processamento Automático
1. Upload foto → OCR → Gemini AI → formulário preenchido → revisão → salvamento

### Análise de Consumo
1. Ordenação por data → filtro de quilometragem → cálculo de distâncias → remoção de irreais → métricas km/L

## 🚀 Deploy

### Variáveis Obrigatórias
- `DATABASE_URL`
- `SESSION_SECRET`

### Variáveis Opcionais
- `GEMINI_API_KEY`
- `SENDGRID_API_KEY`
- `GOOGLE_OAUTH_*`

### Produção
- Gunicorn + ProxyFix
- Pool Connection PostgreSQL
- SSL/HTTPS obrigatório

## 📱 PWA Features

- **Manifest**: Configuração de instalação
- **Service Worker**: Cache e offline
- **Responsive**: Mobile-first design
- **Icons**: Personalizados para todas as plataformas

## 🎨 Design System

### Cores
- Primary: #4A90E2 (Azul)
- Secondary: #28C997 (Verde)
- Dark BG: #1a1a1a
- Card BG: #2d2d2d

### Componentes
- Cards com glass effect
- Botões com gradientes
- Floating labels
- Dark theme consistente

## 📄 Licença

Este projeto é desenvolvido pela **InovaMente Labs** e está licenciado sob a MIT License.

## 🤝 Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para:

1. Fork o projeto
2. Criar uma branch para sua feature
3. Commit suas mudanças
## 🚀 Deploy no GitHub e Vercel

### 1. Configurar Repositório GitHub

1. **Inicializar Git** (se não estiver iniciado):
```bash
git init
git add .
git commit -m "Initial commit - Rodo Stats app"
```

2. **Criar repositório no GitHub**:
   - Acesse [github.com](https://github.com) e crie um novo repositório
   - Nome sugerido: `rodostats`
   - Mantenha público para deploy gratuito no Vercel

3. **Conectar repositório local ao GitHub**:
```bash
git remote add origin https://github.com/SEU_USUARIO/rodostats.git
git branch -M main
git push -u origin main
```

### 2. Deploy no Vercel

1. **Acesse [vercel.com](https://vercel.com)** e faça login com GitHub

2. **Importe o repositório**:
   - Clique em "New Project"
   - Selecione seu repositório `rodostats`
   - Clique "Import"

3. **Configure as variáveis de ambiente**:
```
DATABASE_URL=postgresql://neondb_owner:npg_ArdO9L4sGxUD@ep-sweet-shape-ac6v4rp3-pooler.sa-east-1.aws.neon.tech/neondb
GEMINI_API_KEY=AIzaSyC968LxySN21fpYOIOfqJeMCW9Ja5AOmwg
FLASK_SECRET_KEY=dev-secret-key-change-in-production
```

4. **Deploy automático**:
   - O Vercel detectará automaticamente como aplicação Python
   - O arquivo `vercel.json` já está configurado
   - O `runtime.txt` especifica Python 3.11

5. **Acesse sua aplicação**:
   - URL será algo como: `https://rodostats-seu-usuario.vercel.app`

### ⚠️ Importante para Produção

- Altere o `FLASK_SECRET_KEY` para uma chave segura gerada
- Configure um domínio personalizado se desejar
- Monitore os logs no painel do Vercel

## 🛠️ Desenvolvimento Local

1. Clone o repositório
2. Crie um ambiente virtual:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```
3. Instale as dependências:
```bash
pip install -r requirements.txt
```
4. Configure as variáveis de ambiente ou use as padrões
5. Execute a aplicação:
```bash
python app.py
```

## 🤝 Contribuição

1. Fork o projeto
2. Criar uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abrir um Pull Request

## 📞 Suporte

Para suporte, entre em contato:
- GitHub Issues: [Abrir issue](https://github.com/seu-usuario/rodostats/issues)

---

**Desenvolvido com ❤️ - Rodo Stats**

A aplicação está completa e funcional, oferecendo uma experiência profissional para gestão inteligente de combustível com tecnologias modernas.
