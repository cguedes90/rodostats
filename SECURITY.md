# 🔒 Guia de Segurança - RodoStats

## ⚠️ AÇÃO IMEDIATA NECESSÁRIA

Se você está lendo isso após receber um alerta do GitGuardian sobre credenciais expostas:

### 1. **Rotacionar Credenciais do Banco de Dados**
- Acesse seu painel do [Neon](https://neon.tech)
- Vá em **Settings** → **Reset Password**
- Gere uma nova senha para o banco de dados
- Atualize a variável `DATABASE_URL` no arquivo `.env` local
- Atualize a variável `DATABASE_URL` nas configurações do Vercel

### 2. **Atualizar Secrets no Vercel**
```bash
# Via CLI do Vercel
vercel env rm DATABASE_URL
vercel env add DATABASE_URL

# Ou via Dashboard:
# https://vercel.com/seu-projeto/settings/environment-variables
```

### 3. **Verificar Git History**
As credenciais antigas ainda estão no histórico do Git. Para removê-las completamente:

```bash
# CUIDADO: Isso reescreve o histórico do Git!
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch app.py .env.example" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (use com cautela!)
git push origin --force --all
```

**⚠️ AVISO**: Isso afetará colaboradores. Coordene antes de executar!

---

## 🛡️ Boas Práticas de Segurança

### ✅ O QUE FAZER

1. **Usar Variáveis de Ambiente**
   ```python
   # ✅ CORRETO
   DATABASE_URL = os.environ.get('DATABASE_URL')

   # ❌ ERRADO
   DATABASE_URL = 'postgresql://user:pass@host/db'
   ```

2. **Arquivo `.env` Local**
   ```bash
   # Criar .env baseado no exemplo
   cp .env.example .env

   # Editar com suas credenciais REAIS
   nano .env

   # NUNCA commitar!
   ```

3. **Gerar Secrets Fortes**
   ```python
   # Gerar SESSION_SECRET
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. **Configurar Vercel Corretamente**
   - Dashboard → Settings → Environment Variables
   - Adicionar todas as variáveis do `.env.example`
   - Separar por ambiente (Production, Preview, Development)

### ❌ O QUE NÃO FAZER

1. **NUNCA** commitar arquivos com credenciais:
   - ❌ `.env`
   - ❌ Hardcoded passwords em código
   - ❌ API keys no código
   - ❌ Tokens de acesso

2. **NUNCA** usar credenciais de exemplo em produção:
   - ❌ `your-secret-key-here`
   - ❌ `password123`
   - ❌ Defaults do `.env.example`

3. **NUNCA** compartilhar credenciais:
   - ❌ Slack, Discord, WhatsApp
   - ❌ Email sem criptografia
   - ❌ Issues públicas no GitHub

---

## 🔐 Checklist de Segurança

- [ ] `.env` está no `.gitignore`
- [ ] `.env.example` não contém credenciais reais
- [ ] Todas as credenciais usam `os.environ.get()`
- [ ] Secrets rotacionados após vazamento
- [ ] Vercel configurado com variáveis corretas
- [ ] 2FA ativado em serviços críticos (GitHub, Vercel, Neon)
- [ ] Logs não exibem credenciais
- [ ] Rate limiting configurado em APIs
- [ ] HTTPS enforçado em produção

---

## 📚 Recursos Adicionais

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Neon Security Best Practices](https://neon.tech/docs/security)
- [Vercel Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)
- [GitGuardian Docs](https://docs.gitguardian.com/)

---

## 🆘 Precisa de Ajuda?

Se suspeitar de vazamento de credenciais:

1. **Rotacione IMEDIATAMENTE** todas as credenciais
2. Revise logs de acesso suspeitos
3. Notifique a equipe
4. Documente o incidente

**Em caso de dúvida, SEMPRE erre pelo lado da cautela!**
