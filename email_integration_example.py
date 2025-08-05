# Exemplo de integração dos templates de email no app.py
# Adicione estas importações no topo do arquivo:

from email_service import EmailService, configure_email_settings

# No final da configuração do app (após criar o app):
configure_email_settings(app)
email_service = EmailService(app)

# Exemplo de uso após registro de usuário:
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # ... código de registro existente ...
        
        # Após criar o usuário com sucesso:
        if user_created_successfully:
            # Gerar código de verificação
            verification_code = email_service.generate_verification_code()
            
            # Salvar código no banco (você precisará adicionar este campo ao modelo User)
            user.verification_code = verification_code
            user.email_verified = False
            db.session.commit()
            
            # Enviar email de boas-vindas
            verification_url = url_for('verify_email', token=user.id, code=verification_code, _external=True)
            
            # Escolha um dos emails:
            # 1. Email de boas-vindas simples
            email_service.send_welcome_email(
                user_email=user.email,
                user_name=user.name,
                app_url=url_for('dashboard', _external=True)
            )
            
            # OU
            
            # 2. Email de verificação de conta
            email_service.send_email_verification(
                user_email=user.email,
                user_name=user.name,
                verification_code=verification_code,
                verification_url=verification_url
            )
            
            flash('Conta criada! Verifique seu email para ativar.', 'success')
            return redirect(url_for('login'))

# Exemplo para reset de senha:
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Gerar código de reset
            reset_code = email_service.generate_verification_code(8)
            reset_token = email_service.generate_reset_token()
            
            # Salvar no banco (adicionar campos no modelo User)
            user.reset_code = reset_code
            user.reset_token = reset_token
            user.reset_expires = datetime.utcnow() + timedelta(minutes=15)
            db.session.commit()
            
            # Enviar email
            reset_url = url_for('reset_password', token=reset_token, _external=True)
            
            email_service.send_password_reset_email(
                user_email=user.email,
                user_name=user.name,
                reset_code=reset_code,
                reset_url=reset_url,
                user_ip=request.remote_addr
            )
            
        flash('Se o email existir, você receberá instruções para resetar a senha.', 'info')
        return redirect(url_for('login'))

# Verificação de email:
@app.route('/verify-email/<int:user_id>/<code>')
def verify_email(user_id, code):
    user = User.query.get(user_id)
    
    if user and user.verification_code == code:
        user.email_verified = True
        user.verification_code = None
        db.session.commit()
        
        flash('Email verificado com sucesso!', 'success')
        return redirect(url_for('dashboard'))
    
    flash('Código de verificação inválido.', 'error')
    return redirect(url_for('login'))

# Configurações de email para produção (adicionar ao .env):
"""
SMTP_USERNAME=seu_email@gmail.com
SMTP_PASSWORD=sua_app_password_do_gmail
SENDER_EMAIL=noreply@rodostats.com
APP_URL=https://rodostats.vercel.app
"""
