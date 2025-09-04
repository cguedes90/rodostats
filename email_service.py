"""
Email service for Rodo Stats application
Handles sending different types of emails with professional templates
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import render_template, current_app
import secrets
import string

class EmailService:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize email service with Flask app"""
        self.smtp_server = app.config.get('SMTP_SERVER', 'smtp.zoho.com')
        self.smtp_port = app.config.get('SMTP_PORT', 587)
        self.smtp_username = app.config.get('SMTP_USERNAME', 'contato@inovamentelabs.com.br')
        self.smtp_password = app.config.get('SMTP_PASSWORD')
        self.sender_email = app.config.get('SENDER_EMAIL', 'contato@inovamentelabs.com.br')
        self.sender_name = app.config.get('SENDER_NAME', 'Rodo Stats - InovaMente Labs')
    
    def _send_email(self, to_email, subject, html_content, text_content=None):
        """Send email using SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text version if provided
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML version
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def generate_verification_code(self, length=6):
        """Generate a random verification code"""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    def generate_reset_token(self, length=32):
        """Generate a secure reset token"""
        return secrets.token_urlsafe(length)
    
    def send_welcome_email(self, user_email, user_name, app_url=None):
        """Send welcome email to new user"""
        if not app_url:
            app_url = current_app.config.get('APP_URL', 'https://rodostats.vercel.app')
        
        context = {
            'user_name': user_name,
            'user_email': user_email,
            'registration_date': datetime.now().strftime('%d/%m/%Y às %H:%M'),
            'app_url': app_url,
            'current_year': datetime.now().year
        }
        
        html_content = render_template('emails/welcome.html', **context)
        subject = f"🚗 Bem-vindo ao Rodo Stats, {user_name}!"
        
        return self._send_email(user_email, subject, html_content)
    
    def send_password_reset_email(self, user_email, user_name, reset_code, reset_url, user_ip=None):
        """Send password reset email"""
        context = {
            'user_name': user_name,
            'user_email': user_email,
            'reset_code': reset_code,
            'reset_url': reset_url,
            'request_date': datetime.now().strftime('%d/%m/%Y às %H:%M'),
            'user_ip': user_ip or 'Não disponível',
            'current_year': datetime.now().year
        }
        
        html_content = render_template('emails/password_reset.html', **context)
        subject = f"🔐 Redefinir senha - Rodo Stats"
        
        return self._send_email(user_email, subject, html_content)
    
    def send_email_verification(self, user_email, user_name, verification_code, verification_url):
        """Send email verification"""
        context = {
            'user_name': user_name,
            'user_email': user_email,
            'verification_code': verification_code,
            'verification_url': verification_url,
            'registration_date': datetime.now().strftime('%d/%m/%Y às %H:%M'),
            'current_year': datetime.now().year
        }
        
        html_content = render_template('emails/email_verification.html', **context)
        subject = f"✉️ Confirme seu email - Rodo Stats"
        
        return self._send_email(user_email, subject, html_content)
    
    def send_account_security_alert(self, user_email, user_name, activity_type, user_ip=None):
        """Send security alert for important account activities"""
        context = {
            'user_name': user_name,
            'user_email': user_email,
            'activity_type': activity_type,
            'activity_date': datetime.now().strftime('%d/%m/%Y às %H:%M'),
            'user_ip': user_ip or 'Não disponível',
            'current_year': datetime.now().year
        }
        
        # This would need a separate template
        subject = f"🛡️ Atividade na sua conta - Rodo Stats"
        
        # For now, use a simple HTML template
        html_content = f"""
        <h2>Atividade detectada na sua conta</h2>
        <p>Olá {user_name},</p>
        <p>Detectamos a seguinte atividade na sua conta:</p>
        <ul>
            <li><strong>Atividade:</strong> {activity_type}</li>
            <li><strong>Data/Hora:</strong> {context['activity_date']}</li>
            <li><strong>IP:</strong> {context['user_ip']}</li>
        </ul>
        <p>Se você não reconhece esta atividade, entre em contato conosco imediatamente.</p>
        <hr>
        <p><small>© {context['current_year']} InovaMente Labs - Rodo Stats</small></p>
        """
        
        return self._send_email(user_email, subject, html_content)
    
    def send_fleet_invite_email(self, invitee_email, invitee_name, fleet_name, inviter_name, role, accept_url, message=None):
        """Send fleet invitation email"""
        from datetime import datetime, timedelta
        
        # Role display mapping
        role_mapping = {
            'owner': 'Proprietário',
            'admin': 'Administrador', 
            'manager': 'Gerente',
            'user': 'Usuário'
        }
        
        context = {
            'invitee_email': invitee_email,
            'invitee_name': invitee_name or 'Colega',
            'fleet_name': fleet_name,
            'inviter_name': inviter_name,
            'role': role,
            'role_display': role_mapping.get(role, 'Usuário'),
            'accept_url': accept_url,
            'message': message,
            'invite_date': datetime.now().strftime('%d/%m/%Y às %H:%M'),
            'expiry_date': (datetime.now() + timedelta(days=7)).strftime('%d/%m/%Y'),
            'current_year': datetime.now().year
        }
        
        html_content = render_template('emails/fleet_invite.html', **context)
        subject = f"🚛 Convite para frota: {fleet_name} - Rodo Stats"
        
        return self._send_email(invitee_email, subject, html_content)

# Example usage functions
def setup_email_service(app):
    """Setup email service with Flask app"""
    email_service = EmailService(app)
    return email_service

# Configuration example for Flask app
def configure_email_settings(app):
    """Configure email settings for the app"""
    app.config.update({
        'SMTP_SERVER': 'smtp.zoho.com',
        'SMTP_PORT': 587,
        'SMTP_USERNAME': os.getenv('SMTP_USERNAME', 'contato@inovamentelabs.com.br'),
        'SMTP_PASSWORD': os.getenv('SMTP_PASSWORD'),  # Zoho app password
        'SENDER_EMAIL': os.getenv('SENDER_EMAIL', 'contato@inovamentelabs.com.br'),
        'SENDER_NAME': 'Rodo Stats - InovaMente Labs',
        'APP_URL': os.getenv('APP_URL', 'https://rodostats.vercel.app')
    })
