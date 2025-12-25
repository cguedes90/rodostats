# Changelog - RodoStats

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [2.1.0] - 2025-12-25

### 🚨 CRÍTICO - Segurança
- **Removidas** credenciais hardcoded do PostgreSQL em `app.py`
- **Removidas** senhas e URLs sensíveis de `.env.example`
- **Implementada** validação obrigatória de variáveis de ambiente
- **Adicionado** `SECURITY.md` com guia de ação pós-vazamento
- Sistema agora **FALHA** se `DATABASE_URL` ou `SESSION_SECRET` não estiverem configuradas

### ✨ Melhorias de UX

#### Feedback Visual de IA
- Animação de borda verde + glow nos campos preenchidos pela IA
- Checkmark ✓ ao lado dos labels dos campos processados
- SweetAlert2 com lista detalhada de campos preenchidos
- Toast de sucesso com timer e progress bar
- Mensagem de warning se IA não extrair dados
- Box-shadow verde pulsante por 3 segundos

#### Links e Navegação
- "Abastecer Agora" agora direciona para `add_fuel()` corretamente
- "Manutenção" agora direciona para `maintenance_list()`
- Fim da confusão de todos os links levarem para `vehicles()`

#### Responsividade Mobile
- **Tablets (< 992px)**: Layout otimizado para tablets
- **Mobile (< 768px)**:
  - Cards de veículos ocupam 100% da largura
  - Estatísticas em 2 colunas
  - Botões maiores para touch (min 44px)
  - Tabelas com fonte reduzida
- **Mobile pequeno (< 480px)**:
  - Ações rápidas em 1 coluna
  - Estatísticas em 1 coluna
  - Esconde colunas menos importantes em tabelas
  - Ícones e títulos reduzidos

### 🎨 Design

#### Sistema de Cores Padronizado
- **Verde (#28a745)**: Sucesso, OK, Ativo, Completado
- **Amarelo (#ffc107)**: Aviso, Atenção, Pendente, Arquivado
- **Vermelho (#dc3545)**: Erro, Crítico, Inativo
- **Azul claro (#17a2b8)**: Informação
- **Azul (#4A90E2)**: Principal, Destaque

Variáveis CSS globais em `:root` para consistência.

### 🧪 Testes Automatizados

#### Criado `tests/test_app.py` com 11 testes:
- **TestSecurityConfig**: Verifica ausência de credenciais hardcoded
- **TestRoutesPublic**: Login, register acessíveis
- **TestRoutesProtected**: Dashboard, vehicles requerem autenticação
- **TestUserRegistration**: Registro e detecção de duplicatas
- **TestAPIEndpoints**: APIs requerem autenticação
- **TestCacheHeaders**: Verificação de cache control
- **TestSQLInjectionPrevention**: Proteção contra SQL injection
- **TestXSSPrevention**: Proteção contra XSS

#### Dependências de Desenvolvimento
- pytest + pytest-flask + pytest-cov
- bandit (análise de segurança)
- black + flake8 (qualidade de código)
- faker (dados de teste)

### 📦 Arquivos Modificados
- `app.py`: Validação obrigatória de env vars, versão 2.1.0
- `.env.example`: Limpo, sem credenciais reais, documentado
- `templates/add_fuel_record.html`: Feedback visual IA com animações
- `templates/dashboard.html`: Links corrigidos, responsividade mobile
- `templates/vehicles.html`: Responsividade mobile otimizada
- `templates/base.html`: Sistema de cores padronizado
- `SECURITY.md`: Guia completo de segurança
- `tests/test_app.py`: Suite de testes automatizados
- `requirements-dev.txt`: Dependências de desenvolvimento

### 🔧 Infraestrutura
- Cache busting com timestamp dinâmico
- Meta tags HTTP para desabilitar cache
- Context processor para versão em todos os templates
- Sistema de notificação de nova versão com localStorage

---

## [2.0.0] - 2025-12-25

### ✨ Reformulação Completa do Dashboard

#### Sistema de Boas-Vindas Inteligente
- Saudação contextual baseada no horário (Bom dia/tarde/noite)
- Mensagem personalizada baseada no histórico do usuário
- Sistema de notificações inteligentes
- Métricas principais em destaque

#### Ações Rápidas - NOVO FOCO
- 4 cards grandes e visuais para ações essenciais
- Hover effects e animações suaves
- Design card-based para melhor usabilidade

#### Reorganização Hierárquica
1. Boas-vindas + Notificações (primeiro contato)
2. Ações Rápidas (o que fazer agora?)
3. Resumo Essencial (métricas chave)
4. Insights IA (informações úteis)
5. Últimos registros (histórico recente)
6. Recursos avançados (funcionalidades extras, colapsados)

### 🎯 Sistema Inteligente de Arquivamento

#### Funcionalidades
- Modal com escolha: Arquivar ou Excluir Permanentemente
- API endpoint para contar registros em tempo real
- Soft delete (arquivamento) preserva histórico
- Hard delete opcional remove tudo
- Seção "Veículos Arquivados" colapsável
- Botão de reativar veículos

#### Melhorias de UX
- SweetAlert2 modal com radio buttons
- Preview dinâmico de quantos registros serão afetados
- Cards arquivados com estilo visual diferenciado
- Mensagens flash contextuais

---

## [1.x.x] - Versões Anteriores

### Sistema Base
- Flask + PostgreSQL (Neon)
- Sistema de autenticação com Flask-Login
- CRUD de veículos e abastecimentos
- Dashboard com gráficos (Chart.js)
- Integração com IA (Groq)
- PWA com suporte offline
- Upload de imagens de cupom fiscal
- Cálculos automáticos de consumo
- Exportação de relatórios

---

## Links Úteis

- **Repositório**: https://github.com/cguedes90/rodostats
- **Deploy**: https://rodostats.vercel.app
- **Documentação de Segurança**: [SECURITY.md](./SECURITY.md)
- **Testes**: `pytest tests/ -v`

---

## Como Contribuir

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'feat: Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## Licença

Este projeto é privado e proprietário.
