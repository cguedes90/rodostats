# -*- coding: utf-8 -*-
# Rodo Stats - Controle Inteligente de Combustivel
# Desenvolvido por InovaMente Labs

import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import re
import json
import base64
import io
import csv
import secrets
import traceback
try:
    from PIL import Image
except ImportError:
    Image = None
try:
    from groq import Groq
    # Usar Groq gratuito - muito mais rápido que Gemini!
    groq_client = Groq(api_key=os.environ.get('GROQ_API_KEY', 'gsk_demo_key'))  # Demo key funciona por um tempo
except ImportError:
    groq_client = None

# Configuracao inicial
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://neondb_owner:npg_ArdO9L4sGxUD@ep-sweet-shape-ac6v4rp3-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Configurações de sessão mais simples para debug
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = False  # Relaxar para debug
app.config['SESSION_COOKIE_SAMESITE'] = None   # Relaxar para debug

# Proxy fix para producao
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Banco de dados
db = SQLAlchemy(app)

# Configuração do Flask-Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.zoho.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'contato@inovamentelabs.com.br')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'contato@inovamentelabs.com.br')

mail = Mail(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para acessar esta página.'

# Configurar Groq IA (Gratuito!)
if groq_client:
    print("[OK] Groq IA configurado com sucesso (GRATUITO!)")
else:
    print("[AVISO] Groq IA nao disponivel")

# === MIDDLEWARE HTTPS ===

@app.before_request
def force_https():
    """Força HTTPS em produção"""
    if not request.is_secure and app.config.get('FLASK_ENV') == 'production':
        # Verificar se não é localhost/desenvolvimento
        if 'localhost' not in request.host and '127.0.0.1' not in request.host:
            return redirect(request.url.replace('http://', 'https://'), code=301)

# === FUNÇÕES DE EMAIL ===

def send_email(to, subject, template, **kwargs):
    """Envia email usando template HTML"""
    try:
        print(f"[EMAIL] Tentando enviar email para: {to}")
        print(f"[EMAIL] Assunto: {subject}")
        print(f"[EMAIL] Template: {template}")
        print(f"[EMAIL] Servidor: {app.config.get('MAIL_SERVER', 'NÃO CONFIGURADO')}")
        print(f"[EMAIL] Porta: {app.config.get('MAIL_PORT', 'NÃO CONFIGURADO')}")
        print(f"[EMAIL] Username: {app.config.get('MAIL_USERNAME', 'NÃO CONFIGURADO')}")
        print(f"[EMAIL] Remetente: {app.config.get('MAIL_DEFAULT_SENDER', 'NÃO CONFIGURADO')}")
        
        msg = Message(
            subject,
            recipients=[to],
            html=render_template(template, **kwargs),
            sender=app.config['MAIL_DEFAULT_SENDER']
        )
        
        print(f"[EMAIL] Mensagem criada, enviando...")
        mail.send(msg)
        print(f"[EMAIL] ✅ Email enviado com sucesso para {to}")
        return True
    except Exception as e:
        print(f"[EMAIL] ❌ ERRO ao enviar email para {to}: {str(e)}")
        print(f"[EMAIL] Tipo do erro: {type(e).__name__}")
        import traceback
        print(f"[EMAIL] Stack trace: {traceback.format_exc()}")
        return False

def send_welcome_email(user):
    """Envia email de boas-vindas"""
    from datetime import datetime
    
    registration_date = datetime.now().strftime("%d/%m/%Y às %H:%M")
    
    return send_email(
        to=user.email,
        subject="🚗 Bem-vindo ao Rodo Stats!",
        template="emails/welcome.html",
        user=user,
        user_name=user.username,
        user_email=user.email,
        registration_date=registration_date
    )

def send_password_reset_email(user, reset_token):
    """Envia email de reset de senha"""
    from datetime import datetime
    
    reset_url = url_for('reset_password', token=reset_token, _external=True)
    reset_code = secrets.token_hex(3).upper()  # Código de 6 caracteres
    request_date = datetime.now().strftime("%d/%m/%Y às %H:%M")
    
    # Tentar obter IP do usuário
    user_ip = "Não disponível"
    try:
        from flask import request as flask_request
        user_ip = flask_request.environ.get('HTTP_X_FORWARDED_FOR', 
                  flask_request.environ.get('REMOTE_ADDR', 'Não disponível'))
    except:
        pass
    
    return send_email(
        to=user.email,
        subject="🔑 Reset de Senha - Rodo Stats",
        template="emails/password_reset.html",
        user=user,
        user_name=user.username,
        user_email=user.email,
        reset_url=reset_url,
        reset_code=reset_code,
        request_date=request_date,
        user_ip=user_ip
    )

def send_email_verification(user, verification_token):
    """Envia email de verificação"""
    verification_url = url_for('verify_email', token=verification_token, _external=True)
    return send_email(
        to=user.email,
        subject="✉️ Confirme seu email - Rodo Stats",
        template="emails/email_verification.html",
        user=user,
        verification_url=verification_url
    )


# === MODELOS ===

class OilChange(db.Model):
    __tablename__ = 'oil_changes'
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    km_at_change = db.Column(db.Integer, nullable=True)
    interval_km = db.Column(db.Integer, nullable=False)
    interval_months = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def next_km(self):
        """Calcula a quilometragem da próxima troca"""
        if self.km_at_change and self.interval_km:
            return self.km_at_change + self.interval_km
        return None
    
    def current_km_remaining(self):
        """Calcula quantos km restam para a próxima troca baseado no último abastecimento"""
        # Primeiro, precisa ter quilometragem da troca registrada
        if not self.km_at_change or not self.interval_km:
            return None
            
        # Próxima troca será na quilometragem da troca + intervalo
        next_km = self.km_at_change + self.interval_km
        
        # Pegar o último abastecimento com odômetro para comparar
        last_fuel = FuelRecord.query.filter_by(vehicle_id=self.vehicle_id).filter(
            FuelRecord.odometer.isnot(None)
        ).order_by(FuelRecord.date.desc()).first()
        
        if last_fuel and last_fuel.odometer:
            remaining = next_km - last_fuel.odometer
            return max(0, remaining)  # Não retornar negativo
        
        return None
    def next_date(self):
        if self.date and self.interval_months:
            return self.date + timedelta(days=30*self.interval_months)
        return None
    
    def projected_next_change_date(self):
        """Calcula projeção da próxima troca baseada no uso mensal de km"""
        if not self.km_at_change or not self.interval_km:
            return None
        
        # Pegar abastecimentos dos últimos 90 dias para calcular média mensal
        ninety_days_ago = datetime.now() - timedelta(days=90)
        recent_records = FuelRecord.query.filter(
            FuelRecord.vehicle_id == self.vehicle_id,
            FuelRecord.date >= ninety_days_ago.date(),
            FuelRecord.odometer.isnot(None)
        ).order_by(FuelRecord.date).all()
        
        if len(recent_records) < 2:
            return None
        
        # Calcular km rodados nos últimos 90 dias
        first_record = recent_records[0]
        last_record = recent_records[-1]
        
        total_km = last_record.odometer - first_record.odometer
        total_days = (last_record.date - first_record.date).days
        
        if total_days <= 0 or total_km <= 0:
            return None
        
        # Calcular km por mês
        km_per_month = (total_km / total_days) * 30
        
        # Calcular quanto falta para próxima troca
        remaining_km = self.current_km_remaining()
        if remaining_km is None or remaining_km <= 0:
            return None
        
        # Calcular quantos meses faltam
        months_until_change = remaining_km / km_per_month
        days_until_change = months_until_change * 30
        
        # Projeção da data
        projected_date = datetime.now() + timedelta(days=days_until_change)
        return projected_date.date(), km_per_month

# === SISTEMA COMPLETO DE MANUTENÇÃO ===

class MaintenanceRecord(db.Model):
    """Registro unificado para todos os tipos de manutenção"""
    __tablename__ = 'maintenance_records'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    
    # Tipo de manutenção
    maintenance_type = db.Column(db.String(50), nullable=False)  
    # Valores: 'oil', 'filter_air', 'filter_fuel', 'filter_oil', 'tires', 'brakes', 
    #          'battery', 'spark_plugs', 'transmission', 'coolant', 'brake_fluid',
    #          'power_steering', 'suspension', 'alignment', 'balancing', 'other'
    
    # Dados principais
    description = db.Column(db.String(255), nullable=False)
    cost = db.Column(db.Float, nullable=True)
    km_at_service = db.Column(db.Integer, nullable=True)
    service_provider = db.Column(db.String(100), nullable=True)  # Oficina/mecânico
    
    # Próximo serviço previsto
    next_service_km = db.Column(db.Integer, nullable=True)
    next_service_date = db.Column(db.Date, nullable=True)
    service_interval_km = db.Column(db.Integer, nullable=True)  # Intervalo em km
    service_interval_months = db.Column(db.Integer, nullable=True)  # Intervalo em meses
    
    # Metadados
    notes = db.Column(db.Text, nullable=True)
    created_by_voice = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    vehicle = db.relationship('Vehicle', backref=db.backref('maintenance_records', lazy=True))
    
    def __repr__(self):
        return f'<MaintenanceRecord {self.maintenance_type} - {self.vehicle_id}>'
    
    @property
    def type_display_name(self):
        """Retorna nome amigável do tipo de manutenção"""
        type_names = {
            'oil': 'Troca de Óleo',
            'filter_air': 'Filtro de Ar',
            'filter_fuel': 'Filtro de Combustível', 
            'filter_oil': 'Filtro de Óleo',
            'tires': 'Pneus',
            'brakes': 'Freios',
            'battery': 'Bateria',
            'spark_plugs': 'Velas de Ignição',
            'transmission': 'Transmissão',
            'coolant': 'Fluido de Arrefecimento',
            'brake_fluid': 'Fluido de Freio',
            'power_steering': 'Direção Hidráulica',
            'suspension': 'Suspensão',
            'alignment': 'Alinhamento',
            'balancing': 'Balanceamento',
            'other': 'Outro'
        }
        return type_names.get(self.maintenance_type, self.maintenance_type.title())
    
    def calculate_next_service(self):
        """Calcula automaticamente o próximo serviço baseado nos intervalos"""
        # Próximo por quilometragem
        if self.km_at_service and self.service_interval_km:
            self.next_service_km = self.km_at_service + self.service_interval_km
        
        # Próximo por data
        if self.date and self.service_interval_months:
            next_date = self.date + timedelta(days=30 * self.service_interval_months)
            self.next_service_date = next_date
    
    def is_due_soon(self, warning_km=500, warning_days=30):
        """Verifica se a manutenção está próxima do vencimento"""
        # Verificar por quilometragem
        if self.next_service_km:
            # Obter última quilometragem registrada
            last_fuel = FuelRecord.query.filter_by(vehicle_id=self.vehicle_id).filter(
                FuelRecord.odometer_reading.isnot(None)
            ).order_by(FuelRecord.date.desc()).first()
            
            if last_fuel and last_fuel.odometer_reading:
                km_remaining = self.next_service_km - last_fuel.odometer_reading
                if km_remaining <= warning_km:
                    return True, f"Faltam {km_remaining}km"
        
        # Verificar por data  
        if self.next_service_date:
            days_remaining = (self.next_service_date - datetime.now().date()).days
            if days_remaining <= warning_days:
                return True, f"Faltam {days_remaining} dias"
        
        return False, None
    
    @staticmethod
    def get_maintenance_intervals(maintenance_type):
        """Retorna intervalos padrão para cada tipo de manutenção"""
        intervals = {
            'oil': {'km': 10000, 'months': 6},
            'filter_air': {'km': 15000, 'months': 12},
            'filter_fuel': {'km': 20000, 'months': 12},
            'filter_oil': {'km': 10000, 'months': 6},
            'tires': {'km': 50000, 'months': 48},
            'brakes': {'km': 30000, 'months': 24},
            'battery': {'km': None, 'months': 36},
            'spark_plugs': {'km': 30000, 'months': 24},
            'transmission': {'km': 60000, 'months': 48},
            'coolant': {'km': 40000, 'months': 24},
            'brake_fluid': {'km': None, 'months': 24},
            'power_steering': {'km': 50000, 'months': 36},
            'suspension': {'km': 80000, 'months': 60},
            'alignment': {'km': 20000, 'months': 12},
            'balancing': {'km': 15000, 'months': 12},
            'other': {'km': None, 'months': None}
        }
        return intervals.get(maintenance_type, {'km': None, 'months': None})
    
    @staticmethod
    def get_type_display(maintenance_type):
        """Retorna o nome amigável para exibição"""
        display_map = {
            'oil': 'Troca de Óleo',
            'filter_air': 'Filtro de Ar',
            'filter_fuel': 'Filtro de Combustível',
            'tires': 'Pneus',
            'brakes': 'Freios',
            'battery': 'Bateria',
            'spark_plugs': 'Velas',
            'transmission': 'Transmissão',
            'other': 'Outros'
        }
        return display_map.get(maintenance_type, 'Manutenção')
    
    @staticmethod
    def get_type_icon(maintenance_type):
        """Retorna o ícone FontAwesome para o tipo"""
        icon_map = {
            'oil': 'fas fa-oil-can',
            'filter_air': 'fas fa-wind',
            'filter_fuel': 'fas fa-gas-pump',
            'tires': 'fas fa-circle',
            'brakes': 'fas fa-hand-paper',
            'battery': 'fas fa-battery-half',
            'spark_plugs': 'fas fa-bolt',
            'transmission': 'fas fa-cogs',
            'other': 'fas fa-wrench'
        }
        return icon_map.get(maintenance_type, 'fas fa-tools')
    
    @staticmethod
    def get_type_badge_class(maintenance_type):
        """Retorna a classe CSS para o badge do tipo"""
        class_map = {
            'oil': 'primary',
            'filter_air': 'info',
            'filter_fuel': 'warning',
            'tires': 'dark',
            'brakes': 'danger',
            'battery': 'success',
            'spark_plugs': 'secondary',
            'transmission': 'primary',
            'other': 'light'
        }
        return class_map.get(maintenance_type, 'secondary')
    
    @staticmethod
    def is_maintenance_due(maintenance_record):
        """Verifica se uma manutenção está vencida"""
        from datetime import date
        
        today = date.today()
        
        # Verificar vencimento por data
        if maintenance_record.next_service_date:
            if today >= maintenance_record.next_service_date:
                return True
        
        # Verificar vencimento por quilometragem (se tiver KM atual do veículo)
        if maintenance_record.next_service_km and maintenance_record.vehicle:
            # Esta funcionalidade requereria um campo odometer atual no veículo
            # Por enquanto, vamos assumir que não está vencida se não tiver data
            pass
        
        return False

# === ROTAS ===

@app.route('/oil_change/<int:vehicle_id>', methods=['GET', 'POST'])
@login_required
def oil_change(vehicle_id):
    vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        km_at_change = request.form.get('km_at_change') or None
        interval_km = int(request.form['interval_km'])
        interval_months = request.form.get('interval_months') or None
        if interval_months:
            interval_months = int(interval_months)
        notes = request.form.get('notes')
        oil = OilChange(
            vehicle_id=vehicle_id,
            km_at_change=km_at_change,
            interval_km=interval_km,
            interval_months=interval_months,
            notes=notes
        )
        db.session.add(oil)
        db.session.commit()
        flash('Troca de óleo registrada com sucesso!', 'success')
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))
    return render_template('oil_change.html', vehicle=vehicle)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    vehicles = db.relationship('Vehicle', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# === SISTEMA DE FROTAS EMPRESARIAIS ===

class Fleet(db.Model):
    """Modelo para empresas/frotas"""
    __tablename__ = 'fleets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(150), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=True)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    
    # Configurações da frota
    subscription_plan = db.Column(db.String(20), default='trial')  # trial, small, enterprise, custom
    max_vehicles = db.Column(db.Integer, default=10)
    max_users = db.Column(db.Integer, default=3)
    features_enabled = db.Column(db.JSON, default=lambda: {
        'dashboard_executive': True,
        'automatic_reports': False,
        'api_access': False,
        'custom_alerts': True
    })
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    trial_ends_at = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    members = db.relationship('FleetMember', backref='fleet', lazy=True, cascade='all, delete-orphan')
    vehicles = db.relationship('Vehicle', backref='fleet', lazy=True)
    
    def __repr__(self):
        return f'<Fleet {self.company_name}>'
    
    @property
    def is_trial_active(self):
        """Verifica se o trial ainda está ativo"""
        if not self.trial_ends_at:
            return False
        return datetime.utcnow() < self.trial_ends_at
    
    @property
    def vehicles_count(self):
        """Conta veículos ativos da frota"""
        return Vehicle.query.filter_by(fleet_id=self.id, is_active=True).count()
    
    @property
    def members_count(self):
        """Conta membros ativos da frota"""
        return FleetMember.query.filter_by(fleet_id=self.id, is_active=True).count()
    
    def can_add_vehicle(self):
        """Verifica se pode adicionar mais veículos"""
        return self.vehicles_count < self.max_vehicles
    
    def can_add_member(self):
        """Verifica se pode adicionar mais membros"""
        return self.members_count < self.max_users

class FleetMember(db.Model):
    """Membros de uma frota (usuários da empresa)"""
    __tablename__ = 'fleet_members'
    
    id = db.Column(db.Integer, primary_key=True)
    fleet_id = db.Column(db.Integer, db.ForeignKey('fleets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Hierarquia de permissões
    role = db.Column(db.String(20), nullable=False, default='user')
    # Roles: owner, admin, manager, user, driver
    
    # Metadados
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    invited_at = db.Column(db.DateTime, nullable=True)
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    user = db.relationship('User', foreign_keys=[user_id], backref='fleet_memberships')
    inviter = db.relationship('User', foreign_keys=[invited_by])
    
    # Índice único para evitar duplicatas
    __table_args__ = (db.UniqueConstraint('fleet_id', 'user_id', name='unique_fleet_member'),)
    
    def __repr__(self):
        return f'<FleetMember {self.user.username} in {self.fleet.company_name}>'
    
    @property
    def is_admin(self):
        return self.role in ['owner', 'admin']
    
    @property
    def is_manager(self):
        return self.role in ['owner', 'admin', 'manager']
    
    @property
    def can_manage_users(self):
        return self.role in ['owner', 'admin']
    
    @property
    def can_view_reports(self):
        return self.role in ['owner', 'admin', 'manager']

class Driver(db.Model):
    """Motoristas da frota"""
    __tablename__ = 'drivers'
    
    id = db.Column(db.Integer, primary_key=True)
    fleet_id = db.Column(db.Integer, db.ForeignKey('fleets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Pode ou não ter conta
    
    # Dados pessoais
    name = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), nullable=True)
    cnh = db.Column(db.String(20), nullable=True)
    cnh_category = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    
    # Metadados
    hired_at = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    fleet_rel = db.relationship('Fleet', backref='drivers')
    user = db.relationship('User', backref='driver_profile')
    
    def __repr__(self):
        return f'<Driver {self.name}>'
    
    @property
    def efficiency_score(self):
        """Calcula score de eficiência do motorista (mock por enquanto)"""
        # TODO: Implementar cálculo real baseado em consumo
        return 85  # Placeholder

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    license_plate = db.Column(db.String(20), unique=True, nullable=True)
    color = db.Column(db.String(30), nullable=True)
    fuel_type = db.Column(db.String(20), nullable=False, default='gasoline')
    tank_capacity = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # === CAMPOS PARA FROTAS ===
    fleet_id = db.Column(db.Integer, db.ForeignKey('fleets.id'), nullable=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True)
    vehicle_type = db.Column(db.String(20), default='car')  # car, truck, van, motorcycle, bus
    department = db.Column(db.String(100), nullable=True)  # Centro de custo
    
    # Dados operacionais para frotas
    current_odometer = db.Column(db.Integer, nullable=True)  # KM atual
    purchase_date = db.Column(db.Date, nullable=True)
    purchase_price = db.Column(db.Float, nullable=True)
    
    # Relacionamentos
    fuel_records = db.relationship('FuelRecord', backref='vehicle', lazy=True, cascade='all, delete-orphan')
    assigned_driver = db.relationship('Driver', backref='assigned_vehicles')
    
    def __repr__(self):
        return f'<Vehicle {self.name} - {self.license_plate}>'
    
    def average_consumption(self):
        """Calcula o consumo medio do veiculo"""
        records = FuelRecord.query.filter_by(vehicle_id=self.id).order_by(FuelRecord.odometer).all()
        if len(records) < 2:
            return 0
        
        total_distance = 0
        total_fuel = 0
        
        for i in range(1, len(records)):
            distance = records[i].odometer - records[i-1].odometer
            if distance > 0:
                total_distance += distance
                total_fuel += records[i].liters
        
        if total_fuel == 0:
            return 0
        
        return total_distance / total_fuel

class FuelRecord(db.Model):
    __tablename__ = 'fuel_records'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    odometer = db.Column(db.Float, nullable=False)
    liters = db.Column(db.Float, nullable=False)
    price_per_liter = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    gas_station = db.Column(db.String(100))
    fuel_type = db.Column(db.String(20), nullable=False, default='gasoline')
    notes = db.Column(db.Text)
    receipt_image = db.Column(db.String(255))
    ai_extracted_data = db.Column(db.Text)  # JSON com dados extraidos pela IA
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FuelRecord {self.date} - {self.liters}L>'
    
    def consumption(self):
        """Calcula o consumo para este abastecimento"""
        previous_record = FuelRecord.query.filter(
            FuelRecord.vehicle_id == self.vehicle_id,
            FuelRecord.odometer < self.odometer
        ).order_by(FuelRecord.odometer.desc()).first()
        
        if not previous_record:
            return 0
        
        distance = self.odometer - previous_record.odometer
        if distance <= 0 or self.liters <= 0:
            return 0
        
        return distance / self.liters

class FleetInvite(db.Model):
    __tablename__ = 'fleet_invites'
    
    id = db.Column(db.Integer, primary_key=True)
    fleet_id = db.Column(db.Integer, db.ForeignKey('fleets.id'), nullable=False)
    inviter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Dados do convidado
    email = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='user')  # owner, admin, manager, user
    message = db.Column(db.Text, nullable=True)
    
    # Controle do convite
    token = db.Column(db.String(100), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, expired, cancelled
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    fleet = db.relationship('Fleet', backref='invites')
    inviter = db.relationship('User', backref='sent_invites')
    
    def __repr__(self):
        return f'<FleetInvite {self.email} -> {self.fleet.name}>'
    
    @property
    def is_expired(self):
        """Verifica se o convite expirou"""
        return datetime.utcnow() > self.expires_at
    
    def generate_token(self):
        """Gera um token único para o convite"""
        import secrets
        self.token = secrets.token_urlsafe(32)
    
    def get_accept_url(self, base_url=None):
        """Gera URL de aceite do convite"""
        if not base_url:
            base_url = 'https://rodostats.vercel.app'
        return f"{base_url}/fleet/accept_invite/{self.token}"

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Null para alertas de frota
    fleet_id = db.Column(db.Integer, db.ForeignKey('fleets.id'), nullable=True)  # Null para alertas individuais
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    
    # Tipo e conteúdo do alerta
    alert_type = db.Column(db.String(50), nullable=False)  # 'fuel_anomaly', 'maintenance_due', 'budget_exceeded', etc
    severity = db.Column(db.String(20), default='info')  # 'critical', 'warning', 'info'
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Dados relacionados (JSON para flexibilidade)
    alert_data = db.Column(db.JSON, nullable=True)
    
    # Status do alerta
    is_active = db.Column(db.Boolean, default=True)
    is_read = db.Column(db.Boolean, default=False)
    dismissed_at = db.Column(db.DateTime, nullable=True)
    dismissed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    user = db.relationship('User', foreign_keys=[user_id], backref='alerts')
    fleet = db.relationship('Fleet', backref='alerts')
    vehicle = db.relationship('Vehicle', backref='alerts')
    dismissed_by_user = db.relationship('User', foreign_keys=[dismissed_by])
    
    def __repr__(self):
        return f'<Alert {self.title}>'
    
    @property
    def icon(self):
        """Ícone baseado no tipo do alerta"""
        icon_map = {
            'fuel_anomaly': 'fas fa-exclamation-triangle text-warning',
            'maintenance_due': 'fas fa-wrench text-danger',
            'maintenance_overdue': 'fas fa-tools text-danger',
            'budget_exceeded': 'fas fa-money-bill-wave text-danger',
            'efficiency_drop': 'fas fa-chart-line text-warning',
            'new_member': 'fas fa-user-plus text-success',
            'system': 'fas fa-cog text-info'
        }
        return icon_map.get(self.alert_type, 'fas fa-bell text-primary')
    
    def mark_as_read(self):
        """Marcar alerta como lido"""
        self.is_read = True
        db.session.commit()
    
    def dismiss(self, user_id):
        """Dispensar alerta"""
        self.is_active = False
        self.dismissed_at = datetime.utcnow()
        self.dismissed_by = user_id
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    print(f"[LOAD_USER] Tentando carregar usuário com ID: {user_id}")
    try:
        user = User.query.get(int(user_id))
        print(f"[LOAD_USER] Usuário carregado: {user.username if user else 'None'}")
        return user
    except Exception as e:
        print(f"[LOAD_USER] Erro ao carregar usuário: {e}")
        return None

# === FUNCOES AUXILIARES ===

def allowed_file(filename):
    """Verifica se o arquivo e uma imagem permitida"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_receipt_with_ai(image_path):
    """Processa cupom fiscal ou imagem da bomba com IA - TEMPORARIAMENTE DESABILITADO"""
    # OCR será reimplementado na FASE 3 com soluções especializadas
    return None
    
    try:
        # OCR será reimplementado na FASE 3
        return None
        
        # Ler a imagem
        if Image:
            image = Image.open(image_path)
        else:
            return None
        
        prompt = """
        Analise esta imagem e determine se é um cupom fiscal de posto de combustível ou uma foto da bomba de combustível.
        
        Se for um CUPOM FISCAL, extraia as seguintes informações:
        - Data do abastecimento
        - Nome do posto
        - Tipo de combustível
        - Quantidade de litros
        - Preço por litro
        - Valor total
        - Observações relevantes
        
        Se for uma FOTO DA BOMBA DE COMBUSTÍVEL, extraia:
        - Tipo de combustível (indicado na bomba)
        - Preço por litro (display da bomba)
        - Quantidade de litros (se visível no display)
        - Valor total (se visível no display)
        - Nome do posto (se visível)
        
        Retorne as informações extraídas em formato JSON:
        {
            "tipo_imagem": "cupom_fiscal" ou "bomba_combustivel",
            "data": "YYYY-MM-DD" ou null,
            "posto": "Nome do posto" ou null,
            "combustivel": "gasolina/etanol/diesel" ou null,
            "litros": 0.0 ou null,
            "preco_litro": 0.0 ou null,
            "total": 0.0 ou null,
            "observacoes": "informações adicionais extraídas" ou null,
            "confianca": "alta/media/baixa"
        }
        
        Se não conseguir extrair alguma informação, use null para esse campo.
        Para o campo "confianca", indique se a extração foi clara e precisa.
        Responda APENAS com o JSON, sem texto adicional.
        """
        
        response = model.generate_content([prompt, image])
        
        if response:
            # Limpar a resposta e extrair JSON
            json_text = response.strip()
            if json_text.startswith('```json'):
                json_text = json_text[7:]
            if json_text.endswith('```'):
                json_text = json_text[:-3]
            
            try:
                result = json.loads(json_text.strip())
                
                # Adicionar informações de contexto
                if result.get('tipo_imagem') == 'bomba_combustivel':
                    if not result.get('observacoes'):
                        result['observacoes'] = 'Dados extraídos da bomba de combustível'
                    else:
                        result['observacoes'] += ' (bomba de combustível)'
                elif result.get('tipo_imagem') == 'cupom_fiscal':
                    if not result.get('observacoes'):
                        result['observacoes'] = 'Dados extraídos do cupom fiscal'
                    else:
                        result['observacoes'] += ' (cupom fiscal)'
                
                return result
            except json.JSONDecodeError:
                return None
        
    except Exception as e:
        print(f"Erro no processamento da IA: {e}")
        return None

def calculate_fuel_efficiency(vehicle_id):
    """Calcula eficiencia de combustivel"""
    records = FuelRecord.query.filter_by(vehicle_id=vehicle_id).filter(
        FuelRecord.odometer.isnot(None)
    ).order_by(FuelRecord.date).all()
    
    if len(records) < 2:
        return {
            'average_consumption': 0,
            'best_consumption': 0,
            'worst_consumption': 0,
            'trend': 'stable',
            'has_data': False
        }
    
    consumptions = []
    for i in range(1, len(records)):
        prev_km = records[i-1].odometer
        curr_km = records[i].odometer
        fuel = records[i].liters
        
        if prev_km and curr_km and prev_km > 0 and curr_km > prev_km and fuel > 0:
            distance = curr_km - prev_km
            # Validar se a distância é razoável (entre 1 e 2000 km por abastecimento)
            if 1 <= distance <= 2000:
                consumption = distance / fuel
                # Validar se o consumo é razoável (entre 3 e 25 km/L)
                if 3 <= consumption <= 25:
                    consumptions.append(consumption)
    
    if not consumptions:
        return {
            'average_consumption': 0,
            'best_consumption': 0,
            'worst_consumption': 0,
            'trend': 'stable',
            'has_data': False
        }
    
    # Calcular tendencia (comparar ultimos 3 com primeiros 3)
    trend = 'stable'
    if len(consumptions) >= 6:
        first_three = sum(consumptions[:3]) / 3
        last_three = sum(consumptions[-3:]) / 3
        
        if last_three > first_three * 1.05:
            trend = 'improving'
        elif last_three < first_three * 0.95:
            trend = 'worsening'
    
    return {
        'average_consumption': sum(consumptions) / len(consumptions),
        'best_consumption': max(consumptions),
        'worst_consumption': min(consumptions),
        'trend': trend,
        'has_data': True
    }

# === SISTEMA DE ALERTAS INTELIGENTES ===

def create_alert(user_id=None, fleet_id=None, vehicle_id=None, alert_type='info', 
                 severity='info', title='', message='', metadata=None):
    """Criar novo alerta no sistema"""
    try:
        alert = Alert(
            user_id=user_id,
            fleet_id=fleet_id,
            vehicle_id=vehicle_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            alert_data=metadata or {}
        )
        
        db.session.add(alert)
        db.session.commit()
        
        print(f"[ALERT] ✅ Alerta criado: {title} ({alert_type})")
        return alert
        
    except Exception as e:
        db.session.rollback()
        print(f"[ALERT] ❌ Erro ao criar alerta: {str(e)}")
        return None

def check_fuel_anomalies():
    """Verificar anomalias de consumo para todos os veículos"""
    try:
        print("[ALERT] 🔍 Verificando anomalias de combustível...")
        
        # Buscar todos os veículos com dados suficientes
        vehicles = Vehicle.query.filter_by(is_active=True).all()
        alerts_created = 0
        
        for vehicle in vehicles:
            # Calcular eficiência atual vs histórica
            efficiency_data = calculate_fuel_efficiency(vehicle.id)
            
            if not efficiency_data.get('has_data') or len(vehicle.fuel_records) < 5:
                continue
            
            # Buscar últimos 3 registros
            recent_records = FuelRecord.query.filter_by(vehicle_id=vehicle.id)\
                .order_by(FuelRecord.date.desc()).limit(3).all()
            
            if len(recent_records) < 3:
                continue
            
            # Calcular consumo médio dos últimos registros
            recent_consumptions = []
            for record in recent_records:
                consumption = record.consumption()
                if consumption > 0:
                    recent_consumptions.append(consumption)
            
            if not recent_consumptions:
                continue
                
            recent_avg = sum(recent_consumptions) / len(recent_consumptions)
            historical_avg = efficiency_data['average_consumption']
            
            # Verificar se há anomalia (consumo 20% pior que a média)
            if recent_avg > 0 and historical_avg > 0:
                deviation = ((historical_avg - recent_avg) / historical_avg) * 100
                
                if deviation > 20:  # Consumo 20% pior
                    # Verificar se já existe alerta similar recente (últimos 7 dias)
                    existing_alert = Alert.query.filter(
                        Alert.vehicle_id == vehicle.id,
                        Alert.alert_type == 'fuel_anomaly',
                        Alert.is_active == True,
                        Alert.created_at >= datetime.utcnow() - timedelta(days=7)
                    ).first()
                    
                    if not existing_alert:
                        # Determinar se é para usuário individual ou frota
                        user_id = vehicle.user_id if not vehicle.fleet_id else None
                        fleet_id = vehicle.fleet_id
                        
                        alert = create_alert(
                            user_id=user_id,
                            fleet_id=fleet_id,
                            vehicle_id=vehicle.id,
                            alert_type='fuel_anomaly',
                            severity='warning',
                            title=f'🚨 Consumo elevado - {vehicle.name}',
                            message=f'O veículo {vehicle.name} está consumindo {deviation:.1f}% mais combustível que o normal. '
                                  f'Consumo atual: {recent_avg:.1f} km/L vs média histórica: {historical_avg:.1f} km/L. '
                                  f'Recomendamos verificar filtros, pneus e agendar manutenção preventiva.',
                            alert_data={
                                'recent_consumption': recent_avg,
                                'historical_consumption': historical_avg,
                                'deviation_percentage': deviation,
                                'records_analyzed': len(recent_consumptions)
                            }
                        )
                        
                        if alert:
                            alerts_created += 1
                            
                            # Enviar notificação por email se for crítico (>30%)
                            if deviation > 30:
                                send_fuel_anomaly_email(vehicle, deviation, recent_avg, historical_avg)
        
        print(f"[ALERT] ✅ Verificação de combustível concluída. {alerts_created} alertas criados.")
        return alerts_created
        
    except Exception as e:
        print(f"[ALERT] ❌ Erro ao verificar anomalias: {str(e)}")
        return 0

def check_maintenance_alerts():
    """Verificar alertas de manutenção vencida ou próxima"""
    try:
        print("[ALERT] 🔧 Verificando alertas de manutenção...")
        
        alerts_created = 0
        today = datetime.now().date()
        
        # Buscar todos os veículos ativos
        vehicles = Vehicle.query.filter_by(is_active=True).all()
        
        for vehicle in vehicles:
            # Buscar última manutenção
            last_maintenance = MaintenanceRecord.query.filter_by(
                vehicle_id=vehicle.id
            ).order_by(MaintenanceRecord.date.desc()).first()
            
            if last_maintenance:
                days_since_maintenance = (today - last_maintenance.date).days
                
                # Alertas baseados no tipo de manutenção
                maintenance_intervals = {
                    'oil_change': 90,      # 3 meses
                    'tire_rotation': 180,  # 6 meses  
                    'brake_service': 365,  # 1 ano
                    'general_service': 180 # 6 meses
                }
                
                interval = maintenance_intervals.get(last_maintenance.service_type, 180)
                days_until_next = interval - days_since_maintenance
                
                # Verificar alertas existentes
                existing_alert = Alert.query.filter(
                    Alert.vehicle_id == vehicle.id,
                    Alert.alert_type.in_(['maintenance_due', 'maintenance_overdue']),
                    Alert.is_active == True,
                    Alert.created_at >= datetime.utcnow() - timedelta(days=7)
                ).first()
                
                alert_needed = False
                alert_type = 'maintenance_due'
                severity = 'info'
                title = ''
                message = ''
                
                if days_until_next <= -7:  # Vencida há mais de 7 dias
                    alert_type = 'maintenance_overdue'
                    severity = 'critical'
                    title = f'🚨 Manutenção vencida - {vehicle.name}'
                    message = f'A manutenção do veículo {vehicle.name} está vencida há {abs(days_until_next)} dias. ' \
                             f'Última manutenção: {last_maintenance.service_type} em {last_maintenance.date.strftime("%d/%m/%Y")}. ' \
                             f'Agende uma revisão imediatamente para evitar problemas maiores.'
                    alert_needed = True
                elif days_until_next <= 7 and days_until_next > -7:  # Próxima em até 7 dias
                    alert_type = 'maintenance_due'
                    severity = 'warning'
                    title = f'⚠️ Manutenção próxima - {vehicle.name}'
                    message = f'A manutenção do veículo {vehicle.name} está próxima (em {days_until_next} dias). ' \
                             f'Última manutenção: {last_maintenance.service_type} em {last_maintenance.date.strftime("%d/%m/%Y")}. ' \
                             f'Recomendamos agendar uma revisão preventiva.'
                    alert_needed = True
                
                if alert_needed and not existing_alert:
                    user_id = vehicle.user_id if not vehicle.fleet_id else None
                    fleet_id = vehicle.fleet_id
                    
                    alert = create_alert(
                        user_id=user_id,
                        fleet_id=fleet_id,
                        vehicle_id=vehicle.id,
                        alert_type=alert_type,
                        severity=severity,
                        title=title,
                        message=message,
                        alert_data={
                            'last_maintenance_date': last_maintenance.date.isoformat(),
                            'last_maintenance_type': last_maintenance.service_type,
                            'days_since_maintenance': days_since_maintenance,
                            'days_until_next': days_until_next,
                            'recommended_interval': interval
                        }
                    )
                    
                    if alert:
                        alerts_created += 1
                        
                        # Enviar email se crítico
                        if severity == 'critical':
                            send_maintenance_alert_email(vehicle, days_until_next, last_maintenance)
            
            else:
                # Veículo sem manutenção registrada - alerta informativo
                existing_alert = Alert.query.filter(
                    Alert.vehicle_id == vehicle.id,
                    Alert.alert_type == 'maintenance_due',
                    Alert.is_active == True,
                    Alert.created_at >= datetime.utcnow() - timedelta(days=30)
                ).first()
                
                if not existing_alert:
                    user_id = vehicle.user_id if not vehicle.fleet_id else None
                    fleet_id = vehicle.fleet_id
                    
                    alert = create_alert(
                        user_id=user_id,
                        fleet_id=fleet_id,
                        vehicle_id=vehicle.id,
                        alert_type='maintenance_due',
                        severity='info',
                        title=f'📋 Registre a primeira manutenção - {vehicle.name}',
                        message=f'O veículo {vehicle.name} não possui registros de manutenção. '
                               f'Registre a primeira manutenção para receber alertas preventivos personalizados.',
                        alert_data={
                            'vehicle_age_months': (today - vehicle.created_at.date()).days // 30,
                            'has_maintenance_records': False
                        }
                    )
                    
                    if alert:
                        alerts_created += 1
        
        print(f"[ALERT] ✅ Verificação de manutenção concluída. {alerts_created} alertas criados.")
        return alerts_created
        
    except Exception as e:
        print(f"[ALERT] ❌ Erro ao verificar manutenção: {str(e)}")
        return 0

def send_fuel_anomaly_email(vehicle, deviation, recent_avg, historical_avg):
    """Enviar email de alerta de anomalia de combustível usando sistema PF"""
    try:
        # Determinar destinatário
        if vehicle.fleet_id:
            # Para frotas, enviar para administradores
            admins = FleetMember.query.filter(
                FleetMember.fleet_id == vehicle.fleet_id,
                FleetMember.role.in_(['owner', 'admin']),
                FleetMember.is_active == True
            ).all()
            
            for admin in admins:
                if admin.user.email:
                    send_email(
                        to=admin.user.email,
                        subject=f"🚨 Alerta Crítico - Consumo Elevado: {vehicle.name}",
                        template="emails/fuel_alert.html",
                        vehicle_name=vehicle.name,
                        deviation=deviation,
                        recent_avg=recent_avg,
                        historical_avg=historical_avg,
                        user_name=admin.user.name or admin.user.username,
                        is_fleet=True,
                        fleet_name=vehicle.fleet.name if vehicle.fleet else '',
                        current_year=datetime.utcnow().year
                    )
        else:
            # Para usuários individuais
            if vehicle.user and vehicle.user.email:
                send_email(
                    to=vehicle.user.email,
                    subject=f"🚨 Alerta - Consumo Elevado: {vehicle.name}",
                    template="emails/fuel_alert.html",
                    vehicle_name=vehicle.name,
                    deviation=deviation,
                    recent_avg=recent_avg,
                    historical_avg=historical_avg,
                    user_name=vehicle.user.name or vehicle.user.username,
                    is_fleet=False,
                    current_year=datetime.utcnow().year
                )
        
    except Exception as e:
        print(f"[ALERT] ❌ Erro ao enviar email de anomalia: {str(e)}")

def send_maintenance_alert_email(vehicle, days_overdue, last_maintenance):
    """Enviar email de alerta de manutenção vencida usando sistema PF"""
    try:
        # Determinar destinatário
        if vehicle.fleet_id:
            # Para frotas, enviar para administradores
            admins = FleetMember.query.filter(
                FleetMember.fleet_id == vehicle.fleet_id,
                FleetMember.role.in_(['owner', 'admin']),
                FleetMember.is_active == True
            ).all()
            
            for admin in admins:
                if admin.user.email:
                    send_email(
                        to=admin.user.email,
                        subject=f"🔧 Manutenção Vencida: {vehicle.name}",
                        template="emails/maintenance_alert.html",
                        vehicle_name=vehicle.name,
                        days_overdue=abs(days_overdue),
                        last_maintenance_type=last_maintenance.service_type,
                        last_maintenance_date=last_maintenance.date.strftime('%d/%m/%Y'),
                        user_name=admin.user.name or admin.user.username,
                        is_fleet=True,
                        fleet_name=vehicle.fleet.name if vehicle.fleet else '',
                        current_year=datetime.utcnow().year
                    )
        else:
            # Para usuários individuais
            if vehicle.user and vehicle.user.email:
                send_email(
                    to=vehicle.user.email,
                    subject=f"🔧 Manutenção Vencida: {vehicle.name}",
                    template="emails/maintenance_alert.html",
                    vehicle_name=vehicle.name,
                    days_overdue=abs(days_overdue),
                    last_maintenance_type=last_maintenance.service_type,
                    last_maintenance_date=last_maintenance.date.strftime('%d/%m/%Y'),
                    user_name=vehicle.user.name or vehicle.user.username,
                    is_fleet=False,
                    current_year=datetime.utcnow().year
                )
        
    except Exception as e:
        print(f"[ALERT] ❌ Erro ao enviar email de manutenção: {str(e)}")

def run_daily_alert_checks():
    """Executar verificações diárias de alertas"""
    print("[ALERT] 🤖 Iniciando verificações diárias de alertas...")
    
    fuel_alerts = check_fuel_anomalies()
    maintenance_alerts = check_maintenance_alerts()
    
    total_alerts = fuel_alerts + maintenance_alerts
    print(f"[ALERT] ✅ Verificações concluídas. Total: {total_alerts} alertas criados")
    
    return total_alerts

# === ROTAS ===

@app.route('/')
def index():
    """Landing page do Rodo Stats"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/service-worker.js')
def service_worker():
    """Service Worker para PWA"""
    try:
        return send_file('static/service-worker.js', mimetype='application/javascript')
    except:
        return '', 404

@app.route('/test-login')
def test_login():
    """Rota de teste para verificar login"""
    if current_user.is_authenticated:
        return f"<h1>Usuário logado: {current_user.username}</h1><p>ID: {current_user.id}</p><p>Email: {current_user.email}</p>"
    else:
        return "<h1>Usuário não logado</h1><a href='/login'>Fazer login</a>"

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login do usuario"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        print(f"[LOGIN] Tentativa de login: {username}")
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            print(f"[LOGIN] Credenciais válidas para {username}")
            session.permanent = True
            login_user(user, remember=True)
            print(f"[LOGIN] Usuário logado: {current_user.is_authenticated}")
            
            # Verificar se há convite pendente
            invite_token = request.args.get('invite_token')
            if invite_token:
                return redirect(url_for('accept_fleet_invite', token=invite_token))
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            print(f"[LOGIN] Credenciais inválidas para {username}")
            flash('Usuario ou senha incorretos', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registro de novo usuario"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validacoes
        if password != confirm_password:
            flash('Senhas nao coincidem', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Nome de usuario ja existe', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email ja cadastrado', 'error')
            return render_template('register.html')
        
        # Criar usuario
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Enviar email de boas-vindas
        if send_welcome_email(user):
            flash('Usuario criado com sucesso! Verifique seu email.', 'success')
        else:
            flash('Usuario criado com sucesso!', 'success')
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """Logout do usuario"""
    logout_user()
    return redirect(url_for('index'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Solicitar reset de senha"""
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        
        if user:
            try:
                # Gerar token simples (em produção, use algo mais seguro)
                reset_token = secrets.token_urlsafe(32)
                
                # Armazenar token na sessão temporariamente
                session[f'reset_token_{user.id}'] = {
                    'token': reset_token,
                    'expires': (datetime.utcnow() + timedelta(hours=1)).isoformat()
                }
                
                print(f"[RESET] Tentando enviar email de reset para: {user.email}")
                
                if send_password_reset_email(user, reset_token):
                    flash('Email de reset enviado! Verifique sua caixa de entrada.', 'success')
                    print(f"[RESET] ✅ Email de reset enviado com sucesso")
                else:
                    flash('Erro ao enviar email. Tente novamente.', 'error')
                    print(f"[RESET] ❌ Falha no envio do email de reset")
            except Exception as e:
                print(f"[RESET] ❌ Erro na função forgot_password: {e}")
                flash('Erro interno. Tente novamente mais tarde.', 'error')
        else:
            print(f"[RESET] ⚠️ Usuário não encontrado para email: {email}")
            # Por segurança, sempre mostrar sucesso
            flash('Se o email existir, você receberá as instruções.', 'info')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset de senha com token"""
    # Buscar usuário pelo token na sessão
    user = None
    for key, data in list(session.items()):
        if key.startswith('reset_token_'):
            if data.get('token') == token:
                # Verificar se não expirou
                expires = datetime.fromisoformat(data['expires'])
                if expires > datetime.utcnow():
                    user_id = int(key.split('_')[-1])
                    user = User.query.get(user_id)
                    break
                else:
                    session.pop(key)
    
    if not user:
        flash('Token inválido ou expirado.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Senhas não coincidem.', 'error')
            return render_template('reset_password.html', token=token)
        
        # Atualizar senha
        user.set_password(password)
        db.session.commit()
        
        # Limpar token
        session.pop(f'reset_token_{user.id}', None)
        
        flash('Senha alterada com sucesso!', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

@app.route('/app')
@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal"""
    print(f"[DASHBOARD] Usuário autenticado: {current_user.is_authenticated}")
    print(f"[DASHBOARD] ID do usuário: {current_user.get_id() if current_user.is_authenticated else 'None'}")
    
    # Processar filtros da URL
    selected_vehicle = request.args.get('vehicle_id', type=int)
    selected_days = request.args.get('days', type=int)
    
    vehicles = Vehicle.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    # Construir query base considerando filtros
    base_query = FuelRecord.query.join(Vehicle).filter(Vehicle.user_id == current_user.id)
    
    if selected_vehicle:
        base_query = base_query.filter(FuelRecord.vehicle_id == selected_vehicle)
    
    if selected_days:
        cutoff_date = datetime.now() - timedelta(days=selected_days)
        base_query = base_query.filter(FuelRecord.date >= cutoff_date.date())
    
    # Estatisticas gerais
    total_vehicles = len(vehicles)
    total_records = base_query.count()
    
    # Ultimos abastecimentos (considerando filtros)
    recent_records = base_query.order_by(FuelRecord.date.desc()).limit(5).all()
    
    # Gastos (considerando filtros)
    if selected_days:
        # Se há filtro de período, usar esse período
        cutoff_date = datetime.now() - timedelta(days=selected_days)
        monthly_expense = base_query.filter(FuelRecord.date >= cutoff_date.date()).with_entities(db.func.sum(FuelRecord.total_cost)).scalar() or 0
    else:
        # Senão, usar gasto do mês atual
        current_month = datetime.now().replace(day=1)
        monthly_query = base_query.filter(FuelRecord.date >= current_month)
        monthly_expense = monthly_query.with_entities(db.func.sum(FuelRecord.total_cost)).scalar() or 0
    
    # Total gasto (considerando filtros)
    total_spent = base_query.with_entities(db.func.sum(FuelRecord.total_cost)).scalar() or 0
    
    # Total de litros (considerando filtros)
    total_liters = base_query.with_entities(db.func.sum(FuelRecord.liters)).scalar() or 0
    
    # Preço médio por litro (considerando filtros)
    avg_price = base_query.with_entities(db.func.avg(FuelRecord.price_per_liter)).scalar() or 0
    
    # Posto favorito (considerando filtros)
    favorite_station_query = base_query.filter(
        FuelRecord.gas_station.isnot(None),
        FuelRecord.gas_station != ''
    ).with_entities(
        FuelRecord.gas_station, 
        db.func.count(FuelRecord.gas_station).label('count')
    ).group_by(FuelRecord.gas_station).order_by(db.text('count DESC')).first()
    
    favorite_station = favorite_station_query[0] if favorite_station_query else "Nenhum"
    
    # Métricas de consumo CORRIGIDAS
    all_records = base_query.order_by(FuelRecord.vehicle_id, FuelRecord.date).all()
    
    total_km = 0
    consumptions = []
    km_last_30_days = 0
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Agrupar por veículo para calcular corretamente
    vehicle_records = {}
    for record in all_records:
        if record.vehicle_id not in vehicle_records:
            vehicle_records[record.vehicle_id] = []
        vehicle_records[record.vehicle_id].append(record)
    
    # Calcular KM para cada veículo separadamente
    for vehicle_id, records in vehicle_records.items():
        if len(records) > 1:
            # Ordenar por data para garantir sequência correta
            records.sort(key=lambda x: x.date)
            
            for i in range(1, len(records)):
                # Só calcular se tem odômetro válido
                if records[i].odometer and records[i-1].odometer:
                    distance = records[i].odometer - records[i-1].odometer
                    
                    # Validar distância (evitar valores absurdos)
                    if 0 < distance <= 2000:  # Entre 0 e 2000 km por abastecimento
                        total_km += distance
                        
                        # Calcular consumo se tiver litros
                        if records[i].liters and records[i].liters > 0:
                            consumption = distance / records[i].liters
                            # Validar consumo (entre 3 e 25 km/l para ser realista)
                            if 3 <= consumption <= 25:
                                consumptions.append(consumption)
                        
                        # Verificar se é dos últimos 30 dias
                        if records[i].date >= thirty_days_ago.date():
                            km_last_30_days += distance
    
    consumption_metrics = {
        'total_km': f"{total_km:,.0f} km" if total_km > 0 else "0 km",
        'average_consumption': f"{sum(consumptions)/len(consumptions):.1f}" if consumptions else "N/A",
        'best_consumption': f"{max(consumptions):.1f}" if consumptions else "N/A",
        'km_last_30_days': f"{km_last_30_days:,.0f} km" if km_last_30_days > 0 else "0 km"
    }
    
    # Preparar dados para graficos
    chart_data = []
    for vehicle in vehicles:
        records = FuelRecord.query.filter_by(vehicle_id=vehicle.id).order_by(FuelRecord.date).all()
        if records:
            chart_data.append({
                'vehicle': vehicle.name,
                'data': [{'date': r.date.strftime('%Y-%m-%d'), 'consumption': r.consumption()} for r in records if r.consumption() > 0]
            })
    
    # Dados mensais para gráficos
    monthly_data = {}
    monthly_data_by_fuel = {}
    fuel_distribution = {}
    
    # Calcular gastos mensais separados por combustível
    monthly_records = db.session.query(
        db.func.to_char(FuelRecord.date, 'YYYY-MM').label('month'),
        FuelRecord.fuel_type,
        db.func.sum(FuelRecord.total_cost).label('total')
    ).join(Vehicle).filter(
        Vehicle.user_id == current_user.id
    ).group_by(
        db.func.to_char(FuelRecord.date, 'YYYY-MM'),
        FuelRecord.fuel_type
    ).order_by(db.func.to_char(FuelRecord.date, 'YYYY-MM')).all()
    
    # Organizar dados por mês e combustível
    for month, fuel_type, total in monthly_records:
        if month not in monthly_data_by_fuel:
            monthly_data_by_fuel[month] = {}
        monthly_data_by_fuel[month][fuel_type] = float(total or 0)
        
        # Manter compatibilidade com gráfico antigo (total por mês)
        if month not in monthly_data:
            monthly_data[month] = 0
        monthly_data[month] += float(total or 0)
    
    # Calcular distribuição de combustível
    fuel_records = db.session.query(
        FuelRecord.fuel_type,
        db.func.sum(FuelRecord.liters).label('total_liters')
    ).join(Vehicle).filter(
        Vehicle.user_id == current_user.id
    ).group_by(FuelRecord.fuel_type).all()
    
    for fuel_type, total_liters in fuel_records:
        fuel_distribution[fuel_type] = float(total_liters or 0)
    
    # Usar template original
    return render_template('dashboard.html', 
                         vehicles=vehicles,
                         total_vehicles=total_vehicles,
                         total_records=total_records,
                         recent_records=recent_records,
                         monthly_expense=monthly_expense,
                         total_spent=total_spent,
                         total_liters=total_liters,
                         avg_price=avg_price,
                         favorite_station=favorite_station,
                         consumption_metrics=consumption_metrics,
                         chart_data=chart_data,
                         monthly_data=monthly_data,
                         monthly_data_by_fuel=monthly_data_by_fuel,
                         fuel_distribution=fuel_distribution,
                         selected_vehicle=selected_vehicle,
                         selected_days=selected_days)

@app.route('/vehicles')
@login_required
def vehicles():
    """Lista de veiculos"""
    vehicles = Vehicle.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    # Calcular resumo da frota dos últimos 30 dias
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Buscar registros dos últimos 30 dias
    recent_records = FuelRecord.query.join(Vehicle).filter(
        Vehicle.user_id == current_user.id,
        FuelRecord.date >= thirty_days_ago.date()
    ).all()
    
    # Calcular métricas dos últimos 30 dias
    fleet_summary = {
        'total_vehicles': len(vehicles),
        'total_records_30d': len(recent_records),
        'total_spent_30d': sum(record.total_cost for record in recent_records) if recent_records else 0,
        'total_liters_30d': sum(record.liters for record in recent_records) if recent_records else 0,
        'avg_consumption_30d': 0
    }
    
    # Calcular consumo médio dos últimos 30 dias
    consumptions_30d = []
    for vehicle in vehicles:
        vehicle_records = [r for r in recent_records if r.vehicle_id == vehicle.id]
        vehicle_records.sort(key=lambda x: x.date)
        
        for i in range(1, len(vehicle_records)):
            if vehicle_records[i].odometer and vehicle_records[i-1].odometer:
                distance = vehicle_records[i].odometer - vehicle_records[i-1].odometer
                if 0 < distance <= 2000 and vehicle_records[i].liters > 0:
                    consumption = distance / vehicle_records[i].liters
                    if 3 <= consumption <= 25:
                        consumptions_30d.append(consumption)
    
    if consumptions_30d:
        fleet_summary['avg_consumption_30d'] = sum(consumptions_30d) / len(consumptions_30d)
    
    return render_template('vehicles.html', vehicles=vehicles, fleet_summary=fleet_summary)

@app.route('/add_vehicle', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    """Adicionar novo veiculo"""
    if request.method == 'POST':
        # Obter placa do formulário, se vazia usar None
        license_plate = request.form.get('license_plate', '').strip()
        if not license_plate:
            license_plate = None
        else:
            license_plate = license_plate.upper()
            
        # Obter cor do formulário, se vazia usar None
        color = request.form.get('color', '').strip()
        if not color:
            color = None
        
        # Obter capacidade do tanque, se vazia usar valor padrão
        tank_capacity = request.form.get('tank_capacity', '').strip()
        if not tank_capacity:
            tank_capacity = 50.0  # Valor padrão reasonable
        else:
            tank_capacity = float(tank_capacity)
        
        vehicle = Vehicle(
            user_id=current_user.id,
            name=request.form['name'],
            brand=request.form['brand'],
            model=request.form['model'],
            year=int(request.form['year']),
            license_plate=license_plate,
            color=color,
            fuel_type=request.form['fuel_type'],
            tank_capacity=tank_capacity
        )
        
        try:
            db.session.add(vehicle)
            db.session.commit()
            
            flash('Veiculo adicionado com sucesso!', 'success')
            return redirect(url_for('vehicles'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao cadastrar veículo. Verifique se a placa já não está em uso.', 'error')
            print(f"Erro ao cadastrar veículo: {e}")
    
    return render_template('add_vehicle.html')

@app.route('/vehicle/<int:vehicle_id>')
@login_required
def vehicle_detail(vehicle_id):
    """Detalhes do veiculo"""
    vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=current_user.id).first_or_404()
    records = FuelRecord.query.filter_by(vehicle_id=vehicle_id).order_by(FuelRecord.date.desc()).all()
    # Calcular estatisticas
    efficiency = calculate_fuel_efficiency(vehicle_id)
    # Ultimos 30 dias
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_expense = db.session.query(db.func.sum(FuelRecord.total_cost)).filter(
        FuelRecord.vehicle_id == vehicle_id,
        FuelRecord.date >= thirty_days_ago
    ).scalar() or 0

    # Alerta de troca de óleo aprimorado
    last_oil = OilChange.query.filter_by(vehicle_id=vehicle_id).order_by(OilChange.date.desc()).first()
    oil_alert = None
    if last_oil:
        # Verificar por km
        last_km = records[0].odometer if records else None
        if last_oil.km_at_change is not None and last_oil.interval_km:
            # Se o usuário informou o km da troca, calcula normalmente
            if last_km is not None:
                km_restante = (last_oil.km_at_change + last_oil.interval_km) - last_km
                if km_restante <= 300:
                    oil_alert = f"Troca de óleo próxima! Faltam {km_restante} km para a próxima troca."
            else:
                # Não há registro de km atual, mas temos intervalo
                oil_alert = "Troca de óleo: não foi possível calcular a quilometragem restante. Informe o km no próximo abastecimento."
        elif last_oil.interval_km:
            # Se não informou km_at_change, mas informou intervalo_km, alerta por tempo
            oil_alert = "Troca de óleo: não foi possível calcular a quilometragem restante. Informe o km no próximo abastecimento."
        # Verificar por data
        if last_oil.interval_months:
            next_date = last_oil.next_date()
            if next_date:
                dias_restantes = (next_date - datetime.now().date()).days
                if dias_restantes <= 15:
                    if oil_alert:
                        oil_alert += f" Troca de óleo por tempo próxima! {next_date.strftime('%d/%m/%Y')}"
                    else:
                        oil_alert = f"Troca de óleo por tempo próxima! {next_date.strftime('%d/%m/%Y')}"

    return render_template('vehicle_detail.html', 
                         vehicle=vehicle, 
                         records=records, 
                         efficiency=efficiency,
                         recent_expense=recent_expense,
                         oil_alert=oil_alert)

@app.route('/add_fuel', methods=['GET', 'POST'])
@login_required
def add_fuel():
    """Adicionar abastecimento - formulário manual"""
    vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    
    if request.method == 'POST':
        # Criar registro de combustível
        record = FuelRecord(
            vehicle_id=int(request.form['vehicle_id']),
            date=datetime.now().date(),
            odometer=float(request.form['odometer']) if request.form.get('odometer') else 0,
            liters=float(request.form['liters']),
            price_per_liter=float(request.form['price_per_liter']) if request.form.get('price_per_liter') else 0,
            total_cost=float(request.form['total_cost']),
            gas_station=request.form.get('gas_station', ''),
            fuel_type=request.form.get('fuel_type', 'Gasolina Comum'),
            notes='',
            full_tank=bool(request.form.get('full_tank'))
        )
        
        # Se não foi informado price_per_liter, calcular
        if not record.price_per_liter and record.liters > 0:
            record.price_per_liter = record.total_cost / record.liters
        
        # Se não foi informado total_cost, calcular
        if not record.total_cost and record.liters > 0 and record.price_per_liter > 0:
            record.total_cost = record.liters * record.price_per_liter
        
        # Se não foi informado liters, calcular
        if not record.liters and record.total_cost > 0 and record.price_per_liter > 0:
            record.liters = record.total_cost / record.price_per_liter
        
        db.session.add(record)
        db.session.commit()
        
        flash('Abastecimento adicionado com sucesso!', 'success')
        return redirect(url_for('vehicle_detail', vehicle_id=record.vehicle_id))
    
    return render_template('add_fuel.html', vehicles=vehicles)

@app.route('/add_fuel_record/<int:vehicle_id>', methods=['GET', 'POST'])
@login_required
def add_fuel_record(vehicle_id):
    """Adicionar registro de combustivel"""
    vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        # Processar imagem se enviada
        ai_data = None
        receipt_filename = None
        
        if 'receipt_image' in request.files:
            file = request.files['receipt_image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                receipt_filename = filename
                
                # Processar com IA
                ai_data = process_receipt_with_ai(file_path)
        
        # Criar registro
        record = FuelRecord(
            vehicle_id=vehicle_id,
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            odometer=float(request.form['odometer']),
            liters=float(request.form['liters']),
            price_per_liter=float(request.form['price_per_liter']),
            total_cost=float(request.form['total_cost']),
            gas_station=request.form.get('gas_station', ''),
            fuel_type=request.form.get('fuel_type', vehicle.fuel_type),
            notes=request.form.get('notes', ''),
            receipt_image=receipt_filename,
            ai_extracted_data=json.dumps(ai_data) if ai_data else None
        )
        
        db.session.add(record)
        db.session.commit()
        
        flash('Registro adicionado com sucesso!', 'success')
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))
    
    # Para GET request, passar data atual para o template
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('add_fuel_record.html', vehicle=vehicle, current_date=current_date)

@app.route('/analytics')
@login_required
def analytics():
    """Pagina de analytics"""
    vehicles = Vehicle.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    # Dados para graficos
    analytics_data = {}
    
    for vehicle in vehicles:
        records = FuelRecord.query.filter_by(vehicle_id=vehicle.id).order_by(FuelRecord.date).all()
        
        if records:
            # Consumo ao longo do tempo
            consumption_data = []
            cost_data = []
            
            for i in range(1, len(records)):
                prev_record = records[i-1]
                curr_record = records[i]
                
                distance = curr_record.odometer - prev_record.odometer
                if distance > 0 and curr_record.liters > 0:
                    consumption = distance / curr_record.liters
                    consumption_data.append({
                        'date': curr_record.date.strftime('%Y-%m-%d'),
                        'consumption': round(consumption, 2)
                    })
                
                cost_data.append({
                    'date': curr_record.date.strftime('%Y-%m-%d'),
                    'cost': curr_record.total_cost
                })
            
            analytics_data[vehicle.name] = {
                'consumption': consumption_data,
                'costs': cost_data,
                'efficiency': calculate_fuel_efficiency(vehicle.id)
            }
    
    return render_template('analytics.html', vehicles=vehicles, analytics_data=analytics_data)

@app.route('/api/process_receipt', methods=['POST'])
@login_required
def api_process_receipt():
    """API para processar nota fiscal com IA"""
    if 'image' not in request.files:
        return jsonify({'error': 'Nenhuma imagem enviada'}), 400
    
    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Arquivo invalido'}), 400
    
    # Salvar temporariamente
    filename = secure_filename(file.filename)
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_' + filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file.save(temp_path)
    
    try:
        # Processar com IA
        result = process_receipt_with_ai(temp_path)
        
        # Remover arquivo temporario
        os.remove(temp_path)
        
        if result:
            return jsonify(result)
        else:
            return jsonify({'error': 'Nao foi possivel processar a imagem'}), 400
            
    except Exception as e:
        # Remover arquivo temporario em caso de erro
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': str(e)}), 500

@app.route('/settings')
@login_required
def settings():
    """Configuracoes do usuario"""
    return render_template('settings.html')

@app.route('/export_data')
@login_required
def export_data():
    """Exportar dados para CSV"""
    # Buscar todos os registros do usuario
    records = db.session.query(FuelRecord, Vehicle).join(Vehicle).filter(
        Vehicle.user_id == current_user.id
    ).order_by(FuelRecord.date.desc()).all()
    
    # Criar CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Cabecalho
    writer.writerow([
        'Data', 'Veiculo', 'Odometro', 'Litros', 'Preco/Litro', 
        'Total', 'Posto', 'Combustivel', 'Consumo', 'Observacoes'
    ])
    
    # Dados
    for record, vehicle in records:
        writer.writerow([
            record.date.strftime('%Y-%m-%d'),
            vehicle.name,
            record.odometer,
            record.liters,
            record.price_per_liter,
            record.total_cost,
            record.gas_station,
            record.fuel_type,
            record.consumption(),
            record.notes
        ])
    
    # Preparar resposta
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        as_attachment=True,
        download_name=f'rodostats_export_{datetime.now().strftime("%Y%m%d")}.csv',
        mimetype='text/csv'
    )

# === ROTA GLOBAL DE TROCA DE ÓLEO ===

# Rota apenas para processar POST do modal de troca de óleo
@app.route('/oil_change_global', methods=['POST'])
@login_required
def oil_change_global():
    try:
        vehicle_id = int(request.form['vehicle_id'])
        
        # Verificar se veículo pertence ao usuário
        vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=current_user.id).first()
        if not vehicle:
            flash('Veículo não encontrado!', 'error')
            return redirect(url_for('oil_list'))
        
        # Converter data corretamente
        date_str = request.form.get('date')
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = datetime.now().date()
        
        km_at_change = request.form.get('km_at_change')
        if km_at_change:
            km_at_change = int(km_at_change)
        else:
            km_at_change = None
            
        interval_km = int(request.form['interval_km'])
        
        interval_months = request.form.get('interval_months')
        if interval_months:
            interval_months = int(interval_months)
        else:
            interval_months = None
            
        notes = request.form.get('notes')
        
        oil = OilChange(
            vehicle_id=vehicle_id,
            date=date,
            km_at_change=km_at_change,
            interval_km=interval_km,
            interval_months=interval_months,
            notes=notes
        )
        db.session.add(oil)
        db.session.commit()
        flash('Troca de óleo registrada com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar troca de óleo: {str(e)}', 'error')
    
    return redirect(url_for('oil_list'))

@app.route('/oil')
@login_required
def oil_list():
    # Lista todas as trocas de óleo dos veículos do usuário
    vehicles = Vehicle.query.filter_by(user_id=current_user.id, is_active=True).all()
    oil_changes = []
    for v in vehicles:
        changes = OilChange.query.filter_by(vehicle_id=v.id).order_by(OilChange.date.desc()).all()
        for c in changes:
            oil_changes.append({
                'vehicle': v,
                'oil': c
            })
    oil_changes = sorted(oil_changes, key=lambda x: x['oil'].date, reverse=True)
    current_date = datetime.now().strftime('%Y-%m-%d')
    current_date_obj = datetime.now().date()
    return render_template('oil_list.html', 
                         oil_changes=oil_changes, 
                         vehicles=vehicles, 
                         current_date=current_date,
                         current_date_obj=current_date_obj)

@app.route('/oil_edit/<int:oil_id>', methods=['POST'])
@login_required
def oil_edit(oil_id):
    try:
        # Buscar a troca de óleo e verificar se pertence ao usuário
        oil_change = OilChange.query.join(Vehicle).filter(
            OilChange.id == oil_id,
            Vehicle.user_id == current_user.id
        ).first()
        
        if not oil_change:
            flash('Troca de óleo não encontrada!', 'error')
            return redirect(url_for('oil_list'))
        
        # Atualizar dados
        date_str = request.form.get('date')
        if date_str:
            oil_change.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        km_at_change = request.form.get('km_at_change')
        if km_at_change:
            oil_change.km_at_change = int(km_at_change)
        else:
            oil_change.km_at_change = None
            
        oil_change.interval_km = int(request.form['interval_km'])
        
        interval_months = request.form.get('interval_months')
        if interval_months:
            oil_change.interval_months = int(interval_months)
        else:
            oil_change.interval_months = None
            
        oil_change.notes = request.form.get('notes')
        
        db.session.commit()
        flash('Troca de óleo atualizada com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar troca de óleo: {str(e)}', 'error')
    
    return redirect(url_for('oil_list'))

@app.route('/oil_delete/<int:oil_id>', methods=['POST'])
@login_required
def oil_delete(oil_id):
    try:
        # Buscar a troca de óleo e verificar se pertence ao usuário
        oil_change = OilChange.query.join(Vehicle).filter(
            OilChange.id == oil_id,
            Vehicle.user_id == current_user.id
        ).first()
        
        if not oil_change:
            flash('Troca de óleo não encontrada!', 'error')
            return redirect(url_for('oil_list'))
        
        db.session.delete(oil_change)
        db.session.commit()
        flash('Troca de óleo excluída com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir troca de óleo: {str(e)}', 'error')
    
    return redirect(url_for('oil_list'))

# === ROTAS DE MANUTENÇÃO ===

@app.route('/maintenance')
@login_required
def maintenance_list():
    """Lista todas as manutenções do usuário"""
    try:
        # Buscar todas as manutenções do usuário
        maintenance_records = MaintenanceRecord.query.join(Vehicle).filter(
            Vehicle.user_id == current_user.id
        ).order_by(MaintenanceRecord.created_at.desc()).all()
        
        # Enriquecer dados para exibição
        for record in maintenance_records:
            # Adicionar propriedades para exibição
            record.type_display = MaintenanceRecord.get_type_display(record.maintenance_type)
            record.type_icon = MaintenanceRecord.get_type_icon(record.maintenance_type)
            record.type_badge_class = MaintenanceRecord.get_type_badge_class(record.maintenance_type)
            record.is_pending = MaintenanceRecord.is_maintenance_due(record)
        
        # Calcular estatísticas
        stats = {
            'total_maintenance': len(maintenance_records),
            'pending_maintenance': sum(1 for r in maintenance_records if r.is_pending),
            'total_cost': sum(r.cost or 0 for r in maintenance_records),
            'by_voice': sum(1 for r in maintenance_records if r.created_by_voice)
        }
        
        # Buscar veículos do usuário para o formulário
        user_vehicles = Vehicle.query.filter_by(user_id=current_user.id, is_active=True).all()
        
        return render_template('maintenance.html', 
                               maintenance_records=maintenance_records,
                               stats=stats,
                               user_vehicles=user_vehicles)
        
    except Exception as e:
        flash(f'Erro ao carregar manutenções: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/maintenance', methods=['POST'])
@login_required
def add_maintenance():
    """Adiciona nova manutenção"""
    try:
        vehicle_id = request.form.get('vehicle_id')
        maintenance_type = request.form.get('maintenance_type')
        description = request.form.get('description')
        cost = request.form.get('cost')
        km_at_service = request.form.get('km_at_service')
        service_provider = request.form.get('service_provider')
        next_service_km = request.form.get('next_service_km')
        next_service_date = request.form.get('next_service_date')
        
        # Validar dados obrigatórios
        if not vehicle_id or not maintenance_type:
            flash('Veículo e tipo de manutenção são obrigatórios!', 'error')
            return redirect(url_for('maintenance_list'))
        
        # Verificar se o veículo pertence ao usuário
        vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=current_user.id).first()
        if not vehicle:
            flash('Veículo não encontrado!', 'error')
            return redirect(url_for('maintenance_list'))
        
        # Criar registro de manutenção
        maintenance_record = MaintenanceRecord(
            vehicle_id=vehicle_id,
            maintenance_type=maintenance_type,
            description=description or MaintenanceRecord.get_type_display(maintenance_type),
            cost=float(cost) if cost else None,
            km_at_service=int(km_at_service) if km_at_service else None,
            service_provider=service_provider,
            next_service_km=int(next_service_km) if next_service_km else None,
            next_service_date=datetime.strptime(next_service_date, '%Y-%m-%d').date() if next_service_date else None,
            created_by_voice=False,
            created_at=datetime.now()
        )
        
        db.session.add(maintenance_record)
        db.session.commit()
        flash('Manutenção registrada com sucesso!', 'success')
        
    except ValueError as e:
        flash(f'Dados inválidos: {str(e)}', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar manutenção: {str(e)}', 'error')
    
    return redirect(url_for('maintenance_list'))

@app.route('/maintenance/<int:maintenance_id>', methods=['DELETE'])
@login_required
def delete_maintenance(maintenance_id):
    """Excluir uma manutenção"""
    try:
        # Buscar a manutenção e verificar se pertence ao usuário
        maintenance = MaintenanceRecord.query.join(Vehicle).filter(
            MaintenanceRecord.id == maintenance_id,
            Vehicle.user_id == current_user.id
        ).first()
        
        if not maintenance:
            return jsonify({'error': 'Manutenção não encontrada'}), 404
        
        db.session.delete(maintenance)
        db.session.commit()
        
        return jsonify({'message': 'Manutenção excluída com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro ao excluir manutenção: {str(e)}'}), 500

# === ROTAS DE FROTAS EMPRESARIAIS ===

@app.route('/fleet/register', methods=['GET', 'POST'])
def fleet_register():
    """Registro de nova frota/empresa"""
    if request.method == 'POST':
        try:
            company_name = request.form.get('company_name')
            contact_name = request.form.get('contact_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            cnpj = request.form.get('cnpj')
            password = request.form.get('password')
            
            # Validações básicas
            if not all([company_name, contact_name, email, password]):
                flash('Todos os campos obrigatórios devem ser preenchidos!', 'error')
                return redirect(url_for('fleet_register'))
            
            # Verificar se email já existe
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email já cadastrado no sistema!', 'error')
                return redirect(url_for('fleet_register'))
            
            # Verificar CNPJ se fornecido
            if cnpj:
                existing_fleet = Fleet.query.filter_by(cnpj=cnpj).first()
                if existing_fleet:
                    flash('CNPJ já cadastrado no sistema!', 'error')
                    return redirect(url_for('fleet_register'))
            
            # Criar usuário administrador da frota
            admin_user = User(
                username=email.split('@')[0],  # Usar parte do email como username
                email=email,
                created_at=datetime.utcnow()
            )
            admin_user.set_password(password)
            
            # Criar frota
            fleet = Fleet(
                name=company_name,
                company_name=company_name,
                cnpj=cnpj,
                email=email,
                phone=phone,
                subscription_plan='trial',
                trial_ends_at=datetime.utcnow() + timedelta(days=30),  # 30 dias de trial
                created_at=datetime.utcnow()
            )
            
            # Salvar no banco
            db.session.add(admin_user)
            db.session.add(fleet)
            db.session.flush()  # Para obter IDs
            
            # Criar membro owner da frota
            fleet_member = FleetMember(
                fleet_id=fleet.id,
                user_id=admin_user.id,
                role='owner',
                joined_at=datetime.utcnow()
            )
            
            db.session.add(fleet_member)
            db.session.commit()
            
            # Login automático
            login_user(admin_user)
            
            flash(f'Frota {company_name} criada com sucesso! Trial de 30 dias ativado.', 'success')
            return redirect(url_for('fleet_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar frota: {str(e)}', 'error')
            return redirect(url_for('fleet_register'))
    
    return render_template('fleet_register.html')

@app.route('/fleet/dashboard')
@login_required
def fleet_dashboard():
    """Dashboard executivo para frotas"""
    # Verificar se usuário pertence a uma frota
    fleet_membership = FleetMember.query.filter_by(
        user_id=current_user.id, 
        is_active=True
    ).first()
    
    if not fleet_membership:
        flash('Você não está associado a nenhuma frota.', 'error')
        return redirect(url_for('dashboard'))
    
    fleet = fleet_membership.fleet
    
    # KPIs da frota
    fleet_vehicles = Vehicle.query.filter_by(fleet_id=fleet.id, is_active=True).all()
    
    # Dados dos últimos 30 dias
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Total de registros de combustível
    fleet_fuel_records = db.session.query(FuelRecord).join(Vehicle).filter(
        Vehicle.fleet_id == fleet.id,
        FuelRecord.date >= thirty_days_ago.date()
    ).all()
    
    # Calcular KPIs
    total_spent = sum(record.total_cost for record in fleet_fuel_records)
    total_liters = sum(record.liters for record in fleet_fuel_records)
    total_vehicles = len(fleet_vehicles)
    
    # Eficiência média da frota
    consumptions = []
    for vehicle in fleet_vehicles:
        efficiency = calculate_fuel_efficiency(vehicle.id)
        if efficiency['has_data']:
            consumptions.append(efficiency['average_consumption'])
    
    avg_fleet_consumption = sum(consumptions) / len(consumptions) if consumptions else 0
    
    # Top veículos por eficiência
    vehicle_efficiency = []
    for vehicle in fleet_vehicles:
        efficiency = calculate_fuel_efficiency(vehicle.id)
        vehicle_efficiency.append({
            'vehicle': vehicle,
            'efficiency': efficiency['average_consumption'] if efficiency['has_data'] else 0,
            'total_records': efficiency.get('total_records', 0)
        })
    
    vehicle_efficiency.sort(key=lambda x: x['efficiency'], reverse=True)
    
    # Estatísticas
    fleet_stats = {
        'total_vehicles': total_vehicles,
        'total_spent_30d': total_spent,
        'total_liters_30d': total_liters,
        'avg_consumption': avg_fleet_consumption,
        'total_records_30d': len(fleet_fuel_records),
        'cost_per_vehicle': total_spent / total_vehicles if total_vehicles > 0 else 0
    }
    
    return render_template('fleet_dashboard.html', 
                         fleet=fleet,
                         fleet_membership=fleet_membership,
                         fleet_stats=fleet_stats,
                         vehicle_efficiency=vehicle_efficiency[:5])  # Top 5

@app.route('/fleet/members')
@login_required 
def fleet_members():
    """Gerenciar membros da frota"""
    # Verificar se usuário pode gerenciar membros
    fleet_membership = FleetMember.query.filter_by(
        user_id=current_user.id, 
        is_active=True
    ).first()
    
    if not fleet_membership or not fleet_membership.can_manage_users:
        flash('Você não tem permissão para gerenciar membros.', 'error')
        return redirect(url_for('fleet_dashboard'))
    
    fleet = fleet_membership.fleet
    members = FleetMember.query.filter_by(fleet_id=fleet.id, is_active=True).all()
    
    return render_template('fleet_members.html', 
                         fleet=fleet,
                         members=members,
                         current_membership=fleet_membership)

@app.route('/fleet/send_invite', methods=['POST'])
@login_required
def send_fleet_invite():
    """Enviar convite para novo membro da frota"""
    try:
        # Verificar se usuário pode gerenciar membros
        fleet_membership = FleetMember.query.filter_by(
            user_id=current_user.id, 
            is_active=True
        ).first()
        
        if not fleet_membership or not fleet_membership.can_manage_users:
            return jsonify({'success': False, 'message': 'Você não tem permissão para convidar membros.'}), 403
        
        # Dados do convite
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        role = request.form.get('role', 'user')
        message = request.form.get('message', '').strip()
        
        if not email:
            return jsonify({'success': False, 'message': 'Email é obrigatório.'}), 400
        
        # Verificar se email já está na frota
        existing_member = FleetMember.query.join(User).filter(
            FleetMember.fleet_id == fleet_membership.fleet_id,
            User.email == email,
            FleetMember.is_active == True
        ).first()
        
        if existing_member:
            return jsonify({'success': False, 'message': 'Este email já pertence à frota.'}), 400
        
        # Verificar se já existe convite pendente
        existing_invite = FleetInvite.query.filter_by(
            fleet_id=fleet_membership.fleet_id,
            email=email,
            status='pending'
        ).first()
        
        if existing_invite and not existing_invite.is_expired:
            return jsonify({'success': False, 'message': 'Já existe um convite pendente para este email.'}), 400
        
        # Cancelar convites antigos se existirem
        if existing_invite:
            existing_invite.status = 'cancelled'
        
        # Criar novo convite
        from datetime import datetime, timedelta
        invite = FleetInvite(
            fleet_id=fleet_membership.fleet_id,
            inviter_id=current_user.id,
            email=email,
            name=name,
            role=role,
            message=message,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        invite.generate_token()
        
        db.session.add(invite)
        db.session.commit()
        
        # Enviar email usando a mesma infraestrutura do sistema PF
        accept_url = invite.get_accept_url(request.host_url.rstrip('/'))
        
        # Mapeamento de roles
        role_mapping = {
            'owner': 'Proprietário',
            'admin': 'Administrador', 
            'manager': 'Gerente',
            'user': 'Usuário'
        }
        
        success = send_email(
            to=email,
            subject=f"🚛 Convite para frota: {fleet_membership.fleet.name} - Rodo Stats",
            template="emails/fleet_invite.html",
            invitee_email=email,
            invitee_name=name or 'Colega',
            fleet_name=fleet_membership.fleet.name,
            inviter_name=current_user.name or current_user.username,
            role=role,
            role_display=role_mapping.get(role, 'Usuário'),
            accept_url=accept_url,
            message=message,
            invite_date=datetime.utcnow().strftime('%d/%m/%Y às %H:%M'),
            expiry_date=(datetime.utcnow() + timedelta(days=7)).strftime('%d/%m/%Y'),
            current_year=datetime.utcnow().year
        )
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'Convite enviado com sucesso para {email}!'
            })
        else:
            # Marcar convite como erro no envio
            invite.status = 'failed'
            db.session.commit()
            return jsonify({
                'success': False, 
                'message': 'Erro ao enviar email. Verifique as configurações.'
            }), 500
            
    except Exception as e:
        db.session.rollback()
        print(f"[FLEET_INVITE] Erro: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500

@app.route('/fleet/accept_invite/<token>')
def accept_fleet_invite(token):
    """Aceitar convite de frota"""
    invite = FleetInvite.query.filter_by(token=token, status='pending').first()
    
    if not invite:
        flash('Convite inválido ou já utilizado.', 'error')
        return redirect(url_for('login'))
    
    if invite.is_expired:
        flash('Este convite expirou. Solicite um novo convite.', 'error')
        return redirect(url_for('login'))
    
    # Se usuário não está logado, redirecionar para login com parâmetro
    if not current_user.is_authenticated:
        return redirect(url_for('login', invite_token=token))
    
    # Se usuário está logado, verificar se o email confere
    if current_user.email.lower() != invite.email.lower():
        flash('Este convite foi enviado para outro email. Faça login com a conta correta.', 'error')
        return redirect(url_for('logout'))
    
    # Verificar se usuário já pertence à frota
    existing_member = FleetMember.query.filter_by(
        user_id=current_user.id,
        fleet_id=invite.fleet_id,
        is_active=True
    ).first()
    
    if existing_member:
        flash('Você já faz parte desta frota.', 'info')
        invite.status = 'accepted'
        invite.accepted_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('fleet_dashboard'))
    
    try:
        # Aceitar convite - criar membership
        membership = FleetMember(
            user_id=current_user.id,
            fleet_id=invite.fleet_id,
            role=invite.role,
            invited_by=invite.inviter_id
        )
        
        db.session.add(membership)
        
        # Marcar convite como aceito
        invite.status = 'accepted'
        invite.accepted_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f'Bem-vindo(a) à frota {invite.fleet.name}!', 'success')
        return redirect(url_for('fleet_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        print(f"[ACCEPT_INVITE] Erro: {str(e)}")
        flash('Erro ao aceitar convite. Tente novamente.', 'error')
        return redirect(url_for('login'))

# === ROTAS ESPECIAIS ===

@app.route('/fleet-demo')
def fleet_demo():
    """Demo para frotas empresariais"""
    return render_template('fleet_demo.html')

@app.route('/api/run_alerts')
@login_required
def api_run_alerts():
    """Executar verificações de alertas manualmente"""
    try:
        total_alerts = run_daily_alert_checks()
        return jsonify({
            'success': True,
            'alerts_created': total_alerts,
            'message': f'{total_alerts} alertas verificados/criados com sucesso!'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao executar alertas: {str(e)}'
        }), 500

@app.route('/capture-lead', methods=['POST'])
def capture_lead():
    """Captura leads do formulário da landing page"""
    try:
        nome = request.form.get('nome')
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        empresa_tamanho = request.form.get('empresa_tamanho')
        mensagem = request.form.get('mensagem', '')
        
        # Enviar email para contato@inovamentelabs.com.br
        send_lead_email(nome, email, telefone, empresa_tamanho, mensagem)
        
        flash('Obrigado pelo interesse! Entraremos em contato em breve.', 'success')
        return redirect(url_for('landing_page'))
        
    except Exception as e:
        print(f"[LEAD] Erro ao capturar lead: {str(e)}")
        flash('Erro ao enviar formulário. Tente novamente.', 'error')
        return redirect(url_for('landing_page'))

def send_lead_email(nome, email, telefone, empresa_tamanho, mensagem):
    """Envia email com informações do lead"""
    try:
        from datetime import datetime
        
        data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 10px;">
                    🚗 Novo Lead - Rodo Stats
                </h2>
                
                <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #334155; margin-top: 0;">Informações do Interessado</h3>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; font-weight: bold; width: 30%;">Nome:</td>
                            <td style="padding: 8px;">{nome}</td>
                        </tr>
                        <tr style="background: #ffffff;">
                            <td style="padding: 8px; font-weight: bold;">Email:</td>
                            <td style="padding: 8px;">{email}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Telefone:</td>
                            <td style="padding: 8px;">{telefone}</td>
                        </tr>
                        <tr style="background: #ffffff;">
                            <td style="padding: 8px; font-weight: bold;">Empresa/Frota:</td>
                            <td style="padding: 8px;">{empresa_tamanho}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Data/Hora:</td>
                            <td style="padding: 8px;">{data_atual}</td>
                        </tr>
                    </table>
                </div>
                
                {f'''
                <div style="background: #ffffff; border-left: 4px solid #2563eb; padding: 20px; margin: 20px 0;">
                    <h4 style="color: #334155; margin-top: 0;">Mensagem:</h4>
                    <p style="margin: 0; font-style: italic;">{mensagem}</p>
                </div>
                ''' if mensagem else ''}
                
                <div style="background: #e0f2fe; padding: 15px; border-radius: 8px; margin-top: 20px;">
                    <p style="margin: 0; font-size: 14px; color: #0277bd;">
                        <strong>💡 Próximos passos sugeridos:</strong><br>
                        • Responder em até 24 horas<br>
                        • Agendar demo personalizada<br>
                        • Apresentar funcionalidades específicas para o tipo de empresa
                    </p>
                </div>
                
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">
                
                <p style="color: #64748b; font-size: 12px; text-align: center; margin: 0;">
                    Email gerado automaticamente pelo sistema Rodo Stats<br>
                    © 2024 InovaMente Labs
                </p>
            </div>
        </body>
        </html>
        """
        
        msg = Message(
            "Captura de Lead RodoStats",
            recipients=['contato@inovamentelabs.com.br'],
            html=html_content,
            sender=app.config['MAIL_DEFAULT_SENDER']
        )
        
        mail.send(msg)
        print(f"[LEAD] ✅ Email enviado com sucesso para contato@inovamentelabs.com.br")
        return True
        
    except Exception as e:
        print(f"[LEAD] ❌ Erro ao enviar email: {str(e)}")
        return False

# === SERVIÇO DE IA AVANÇADA ===
class AIService:
    """Serviço de Inteligência Artificial avançada usando Groq (GRATUITO!)"""
    
    def __init__(self):
        self.client = groq_client
        self.model_name = "llama-3.1-70b-versatile"  # Modelo gratuito e rápido
    
    def is_available(self):
        """Verifica se o serviço de IA está disponível"""
        return self.client is not None
    
    def _call_ai(self, prompt):
        """Função helper para fazer chamadas à IA"""
        if not self.is_available():
            return None
        
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model_name,
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Erro na IA: {e}")
            return None
    
    def analyze_spending_pattern(self, user_data):
        """Analisa padrão de gastos e faz previsões"""
        if not self.is_available():
            return {"error": "IA não disponível"}
        
        try:
            prompt = f"""
            Analise estes dados de combustível de um usuário brasileiro e forneça insights em JSON:
            
            DADOS: {user_data}
            
            Responda em formato JSON com:
            {{
                "previsao_mes_proximo": {{
                    "valor_estimado": float,
                    "litros_estimados": float,
                    "confianca": int
                }},
                "anomalias_detectadas": [
                    {{
                        "tipo": "string",
                        "descricao": "string", 
                        "impacto": "baixo/medio/alto"
                    }}
                ],
                "sugestoes": [
                    {{
                        "categoria": "economia/performance/manutencao",
                        "acao": "string",
                        "economia_potencial": float
                    }}
                ],
                "insights": [
                    "string insight relevante"
                ],
                "score_eficiencia": int
            }}
            
            Base sua análise em padrões de consumo brasileiros, preços regionais, e eficiência de combustível.
            """
            
            response = self._call_ai(prompt)
            
            if response:
                import json
                try:
                    result = json.loads(response.strip())
                    return result
                except json.JSONDecodeError:
                    return {"error": "Resposta inválida da IA"}
            
            return {"error": "Resposta vazia da IA"}
            
        except Exception as e:
            print(f"Erro na análise de IA: {e}")
            return {"error": str(e)}
    
    def generate_fuel_recommendations(self, vehicle_data, current_prices, location="Brasil"):
        """Gera recomendações de combustível baseadas em eficiência"""
        if not self.is_available():
            return []
        
        try:
            prompt = f"""
            Como especialista automotivo no Brasil, recomende o melhor combustível:
            
            VEÍCULO: {vehicle_data}
            PREÇOS: {current_prices}
            LOCALIZAÇÃO: {location}
            
            Responda em JSON com array de recomendações:
            [
                {{
                    "combustivel": "string",
                    "razao": "string explicando o porquê",
                    "economia_estimada": "string com valor/percentual",
                    "prioridade": int,
                    "consideracoes": "string com detalhes técnicos"
                }}
            ]
            
            Considere a regra dos 70% (etanol vantajoso quando <70% do preço da gasolina).
            """
            
            response = self._call_ai(prompt)
            
            if response:
                import json
                try:
                    result = json.loads(response.strip())
                    return result
                except json.JSONDecodeError:
                    return []
            
            return []
            
        except Exception as e:
            print(f"Erro nas recomendações de IA: {e}")
            return []
    
    def detect_maintenance_insights(self, vehicle_records):
        """Detecta insights de manutenção baseados em padrões"""
        if not self.is_available():
            return {}
        
        try:
            prompt = f"""
            Como mecânico especializado, analise estes registros de veículo brasileiro:
            
            REGISTROS: {vehicle_records}
            
            Responda em JSON:
            {{
                "alertas_manutencao": [
                    {{
                        "tipo": "oleo/filtro/pneus/geral",
                        "urgencia": "baixa/media/alta",
                        "descricao": "string",
                        "prazo_sugerido": "string",
                        "custo_estimado": "string"
                    }}
                ],
                "performance_trends": {{
                    "consumo_medio": "melhorando/estavel/piorando",
                    "variacao_percentual": float,
                    "possivel_causa": "string"
                }},
                "proximo_servico": {{
                    "tipo": "string",
                    "km_estimado": int,
                    "data_estimada": "YYYY-MM-DD"
                }},
                "dicas_economia": ["string"]
            }}
            """
            
            response = self._call_ai(prompt)
            
            if response:
                import json
                try:
                    result = json.loads(response.strip())
                    return result
                except json.JSONDecodeError:
                    return {}
            
            return {}
            
        except Exception as e:
            print(f"Erro na análise de manutenção: {e}")
            return {}
    
    def generate_monthly_report(self, monthly_data, user_name="Usuário"):
        """Gera relatório mensal inteligente"""
        if not self.is_available():
            return "Relatório não disponível - IA offline"
        
        try:
            prompt = f"""
            Crie um relatório mensal profissional para {user_name} baseado nestes dados:
            
            DADOS MENSAIS: {monthly_data}
            
            Gere um relatório em português brasileiro, estruturado e profissional, incluindo:
            
            # 📊 RELATÓRIO MENSAL - RODOSTATS
            
            ## 💰 RESUMO EXECUTIVO
            - Gasto total do mês
            - Comparativo com mês anterior
            - Principal insight
            
            ## ⛽ ANÁLISE DE GASTOS
            - Distribuição por combustível
            - Postos mais utilizados
            - Tendências de preço
            
            ## 🚗 EFICIÊNCIA DE COMBUSTÍVEL
            - Consumo médio
            - Melhor/pior performance
            - Fatores que influenciaram
            
            ## 📈 PROJEÇÕES PRÓXIMO MÊS
            - Estimativa de gastos
            - Recomendações
            
            ## 🎯 AÇÕES RECOMENDADAS
            - 3 sugestões práticas de economia
            
            Use formatação markdown, emojis e seja específico com números.
            Mantenha tom profissional mas acessível, como um consultor especializado.
            """
            
            response = self._call_ai(prompt)
            return response if response else "Erro ao gerar relatório"
            
        except Exception as e:
            print(f"Erro no relatório de IA: {e}")
            return f"Erro ao gerar relatório: {str(e)}"
    
    def smart_coach_message(self, user_data, context="dashboard"):
        """Gera mensagem de coach inteligente baseada no contexto"""
        if not self.is_available():
            return None
        
        try:
            prompt = f"""
            Como coach financeiro especializado em combustível, dê uma dica personalizada:
            
            DADOS DO USUÁRIO: {user_data}
            CONTEXTO: {context}
            
            Gere uma mensagem motivacional e útil em português brasileiro:
            - Máximo 2 frases
            - Tom amigável e encorajador  
            - Inclua uma dica prática específica
            - Use dados reais quando possível
            
            Responda apenas com a mensagem, sem formatação JSON.
            """
            
            response = self._call_ai(prompt)
            return response.strip() if response else None
            
        except Exception as e:
            print(f"Erro no coach de IA: {e}")
            return None
    
    def regional_comparative_analysis(self, user_data, user_region="Brasil"):
        """Análise comparativa regional com IA"""
        if not self.model:
            return None
            
        try:
            prompt = f"""
            Analise os dados de combustível do usuário e compare com padrões regionais do Brasil:
            
            DADOS DO USUÁRIO: {user_data}
            REGIÃO: {user_region}
            
            Faça uma análise comparativa considerando:
            - Preços médios de combustível por região no Brasil
            - Consumo típico por tipo de veículo
            - Padrões sazonais de preço
            - Eficiência energética regional
            - Dicas para otimização baseadas na região
            
            Retorne um JSON com esta estrutura:
            {{
                "regional_comparison": {{
                    "user_avg_price": "preço médio do usuário",
                    "region_avg_price": "preço médio da região",
                    "price_difference_percent": "diferença percentual",
                    "user_position": "acima/abaixo/na média"
                }},
                "regional_insights": [
                    "insight específico da região",
                    "comparativo com outras regiões"
                ],
                "optimization_tips": [
                    "dica específica para a região",
                    "sugestão de economia"
                ],
                "seasonal_analysis": {{
                    "current_trend": "tendência atual de preços",
                    "next_months_prediction": "previsão próximos meses",
                    "best_time_to_fuel": "melhor período para abastecer"
                }}
            }}
            
            Responda APENAS com o JSON válido.
            """
            
            response = self._call_ai(prompt)
            if response:
                import json
                return json.loads(response.strip())
            return None
            
        except Exception as e:
            print(f"Erro na análise regional: {e}")
            return None
    
    def process_voice_command(self, transcript, user_id):
        """Processa comando de voz e extrai dados estruturados"""
        if not self.is_available():
            return None
        
        try:
            prompt = f"""
            Você é um assistente especializado em extrair dados de comandos de voz sobre combustível e manutenção automotiva.
            
            COMANDO DE VOZ: "{transcript}"
            
            Analise o texto e extraia informações estruturadas. Identifique se é sobre:
            1. ABASTECIMENTO (valores, litros, tipo combustível, posto, data)  
            2. MANUTENÇÃO (troca óleo, filtros, pneus, freios, bateria, velas, etc)
            3. QUILOMETRAGEM (km rodados, período)
            4. CONSULTA (pergunta sobre dados/estatísticas)
            
            TIPOS DE MANUTENÇÃO RECONHECIDOS:
            - oil: óleo, troca de óleo
            - filter_air: filtro de ar
            - filter_fuel: filtro de combustível
            - filter_oil: filtro de óleo  
            - tires: pneus, pneu
            - brakes: freios, pastilha, disco
            - battery: bateria
            - spark_plugs: velas, velas de ignição
            - transmission: transmissão, câmbio
            - coolant: água, radiador, arrefecimento
            - brake_fluid: fluido de freio
            - power_steering: direção hidráulica
            - suspension: suspensão, amortecedor
            - alignment: alinhamento
            - balancing: balanceamento
            - other: revisão, inspeção, outro
            
            Responda APENAS com JSON neste formato:
            {{
                "tipo": "abastecimento|manutencao|quilometragem|consulta|desconhecido",
                "confianca": 0.0-1.0,
                "dados_extraidos": {{
                    "valor": float ou null,
                    "litros": float ou null, 
                    "tipo_combustivel": "gasolina|etanol|diesel|gnv" ou null,
                    "posto": "string" ou null,
                    "data": "YYYY-MM-DD" ou "hoje" ou "ontem" ou "anteontem" ou null,
                    "tipo_manutencao": "oil|filter_air|filter_fuel|tires|brakes|battery|spark_plugs|other" ou null,
                    "quilometragem": int ou null,
                    "oficina": "string nome da oficina/mecânico" ou null,
                    "descricao": "string resumindo o que foi dito"
                }},
                "acao_sugerida": "salvar_abastecimento|salvar_manutencao|atualizar_km|responder_consulta|pedir_esclarecimento",
                "mensagem_usuario": "string amigável explicando o que foi entendido"
            }}
            
            EXEMPLOS DE COMANDOS:
            - "Abasteci 50 reais de gasolina no posto Shell" → abastecimento
            - "Troquei o óleo ontem, gastei 150 reais" → manutenção (oil)
            - "Fiz revisão completa na oficina do João, 800 reais" → manutenção (other)
            - "Troquei os pneus traseiros, 450 reais" → manutenção (tires)
            - "Substituí a bateria hoje, 280 reais" → manutenção (battery)
            - "Quanto gastei em combustível esse mês?" → consulta
            
            IMPORTANTE:
            - Se não conseguir extrair dados claros, use "desconhecido" e "pedir_esclarecimento"
            - Para valores como "oitenta reais", "cento e cinquenta", converta para números
            - Para datas relativas, use "hoje", "ontem", "anteontem"
            - Para posto/oficina, extraia nomes próprios quando mencionados
            - Seja preciso na extração - melhor pedir esclarecimento que assumir dados incorretos
            - Para revisão completa ou inspeção, use tipo_manutencao: "other"
            """
            
            response = self._call_ai(prompt)
            if response:
                import json
                try:
                    result = json.loads(response.strip())
                    
                    # Validar estrutura básica
                    if all(key in result for key in ['tipo', 'confianca', 'dados_extraidos', 'acao_sugerida', 'mensagem_usuario']):
                        return result
                    
                except json.JSONDecodeError as e:
                    print(f"Erro no JSON do comando de voz: {e}")
                    
            return None
            
        except Exception as e:
            print(f"Erro no processamento de comando de voz: {e}")
            return None

# Instância global do serviço de IA
ai_service = AIService()

def process_maintenance_record_from_voice(voice_data, user_id):
    """
    Processa e salva um registro de manutenção extraído do comando de voz
    
    Args:
        voice_data (dict): Dados extraídos pela IA
        user_id (int): ID do usuário atual
        
    Returns:
        tuple: (success: bool, message: str, maintenance_record: MaintenanceRecord ou None)
    """
    try:
        # Validar dados mínimos necessários
        if not voice_data or not voice_data.get('tipo_manutencao'):
            return False, "Tipo de manutenção não identificado", None
            
        # Obter veículo padrão do usuário (primeiro veículo ativo)
        vehicle = Vehicle.query.filter_by(user_id=user_id, is_active=True).first()
        if not vehicle:
            return False, "Nenhum veículo ativo encontrado", None
            
        # Mapear tipos de manutenção
        maintenance_types = {
            'oil': 'Troca de Óleo',
            'filter_air': 'Filtro de Ar',
            'filter_fuel': 'Filtro de Combustível', 
            'tires': 'Pneus',
            'brakes': 'Freios',
            'battery': 'Bateria',
            'spark_plugs': 'Velas de Ignição',
            'transmission': 'Transmissão',
            'other': 'Manutenção Geral'
        }
        
        maintenance_type = voice_data.get('tipo_manutencao', 'other')
        description = maintenance_types.get(maintenance_type, voice_data.get('descricao', 'Manutenção registrada por voz'))
        
        # Criar registro de manutenção
        maintenance_record = MaintenanceRecord(
            vehicle_id=vehicle.id,
            maintenance_type=maintenance_type,
            description=description,
            cost=voice_data.get('custo'),
            km_at_service=voice_data.get('quilometragem'),
            service_provider=voice_data.get('oficina'),
            created_by_voice=True,
            created_at=datetime.now()
        )
        
        # Calcular próximas manutenções baseado no tipo
        intervals = MaintenanceRecord.get_maintenance_intervals()
        if maintenance_type in intervals:
            interval_data = intervals[maintenance_type]
            
            # Calcular próxima quilometragem
            if maintenance_record.km_at_service and interval_data.get('km_interval'):
                maintenance_record.next_service_km = (
                    maintenance_record.km_at_service + interval_data['km_interval']
                )
            
            # Calcular próxima data
            if interval_data.get('months_interval'):
                maintenance_record.next_service_date = (
                    datetime.now().date() + timedelta(days=interval_data['months_interval'] * 30)
                )
        
        # Salvar no banco
        db.session.add(maintenance_record)
        db.session.commit()
        
        success_message = f"Manutenção '{description}' registrada com sucesso"
        if maintenance_record.cost:
            success_message += f" - Custo: R$ {maintenance_record.cost:.2f}"
        if maintenance_record.km_at_service:
            success_message += f" - KM: {maintenance_record.km_at_service}"
            
        return True, success_message, maintenance_record
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao processar manutenção por voz: {e}")
        return False, f"Erro ao salvar manutenção: {str(e)}", None

# === ROTAS DA API DE IA ===

@app.route('/api/ai/analyze', methods=['GET'])
@login_required
def api_ai_analyze():
    """API para análise inteligente de padrões de gasto"""
    try:
        # Coletar dados do usuário dos últimos 90 dias
        ninety_days_ago = datetime.now() - timedelta(days=90)
        records = FuelRecord.query.join(Vehicle).filter(
            Vehicle.user_id == current_user.id,
            FuelRecord.date >= ninety_days_ago.date()
        ).order_by(FuelRecord.date.desc()).limit(50).all()
        
        if not records:
            return jsonify({"error": "Dados insuficientes para análise"})
        
        # Preparar dados para IA
        user_data = {
            "total_records": len(records),
            "period_days": 90,
            "records": [
                {
                    "date": record.date.isoformat(),
                    "fuel_type": record.fuel_type,
                    "liters": float(record.liters),
                    "total_cost": float(record.total_cost),
                    "price_per_liter": float(record.price_per_liter),
                    "odometer": record.odometer,
                    "gas_station": record.gas_station
                }
                for record in records[:20]  # Limitar para não sobrecarregar IA
            ],
            "user_profile": {
                "member_since": current_user.created_at.isoformat() if current_user.created_at else None,
                "total_vehicles": len(current_user.vehicles)
            }
        }
        
        # Chamar IA
        ai_result = ai_service.analyze_spending_pattern(user_data)
        
        return jsonify(ai_result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/recommendations', methods=['GET'])
@login_required  
def api_ai_recommendations():
    """API para recomendações inteligentes de combustível"""
    try:
        vehicle_id = request.args.get('vehicle_id', type=int)
        
        # Se não especificou veículo, usar o primeiro
        if not vehicle_id:
            vehicle = Vehicle.query.filter_by(user_id=current_user.id, is_active=True).first()
            if not vehicle:
                return jsonify({"error": "Nenhum veículo encontrado"})
        else:
            vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=current_user.id).first()
            if not vehicle:
                return jsonify({"error": "Veículo não encontrado"})
        
        # Dados do veículo
        vehicle_data = {
            "brand": vehicle.brand,
            "model": vehicle.model,
            "year": vehicle.year,
            "engine_type": "flex",  # Assumir flex por padrão no Brasil
            "fuel_records_count": len(vehicle.fuel_records)
        }
        
        # Preços atuais simulados (você pode integrar com API de preços reais)
        current_prices = {
            "gasolina_comum": 5.50,
            "etanol": 3.80,
            "diesel": 5.80
        }
        
        # Chamar IA
        recommendations = ai_service.generate_fuel_recommendations(
            vehicle_data, current_prices
        )
        
        return jsonify({
            "vehicle": vehicle_data,
            "current_prices": current_prices,
            "recommendations": recommendations
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/maintenance', methods=['GET'])
@login_required
def api_ai_maintenance():
    """API para insights de manutenção baseados em IA"""
    try:
        vehicle_id = request.args.get('vehicle_id', type=int)
        
        if not vehicle_id:
            vehicle = Vehicle.query.filter_by(user_id=current_user.id, is_active=True).first()
        else:
            vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=current_user.id).first()
        
        if not vehicle:
            return jsonify({"error": "Veículo não encontrado"})
        
        # Dados dos últimos registros
        recent_records = FuelRecord.query.filter_by(vehicle_id=vehicle.id)\
            .order_by(FuelRecord.date.desc()).limit(20).all()
        
        vehicle_records = {
            "vehicle_info": {
                "brand": vehicle.brand,
                "model": vehicle.model, 
                "year": vehicle.year,
                "created_at": vehicle.created_at.isoformat()
            },
            "recent_records": [
                {
                    "date": record.date.isoformat(),
                    "odometer": record.odometer,
                    "fuel_consumption": record.consumption() if hasattr(record, 'consumption') else None,
                    "liters": float(record.liters),
                    "total_cost": float(record.total_cost)
                }
                for record in recent_records if record.odometer
            ]
        }
        
        # Chamar IA
        maintenance_insights = ai_service.detect_maintenance_insights(vehicle_records)
        
        return jsonify(maintenance_insights)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/coach', methods=['GET'])
@login_required
def api_ai_coach():
    """API para mensagens do coach inteligente"""
    try:
        context = request.args.get('context', 'dashboard')
        
        # Dados resumidos do usuário
        total_spent = db.session.query(db.func.sum(FuelRecord.total_cost))\
            .join(Vehicle).filter(Vehicle.user_id == current_user.id).scalar() or 0
            
        last_month = datetime.now() - timedelta(days=30)
        monthly_spent = db.session.query(db.func.sum(FuelRecord.total_cost))\
            .join(Vehicle).filter(
                Vehicle.user_id == current_user.id,
                FuelRecord.date >= last_month.date()
            ).scalar() or 0
        
        user_data = {
            "total_spent": float(total_spent),
            "monthly_spent": float(monthly_spent),
            "vehicles_count": len(current_user.vehicles),
            "member_since_days": (datetime.now() - current_user.created_at).days if current_user.created_at else 0
        }
        
        # Chamar IA
        message = ai_service.smart_coach_message(user_data, context)
        
        return jsonify({
            "message": message,
            "context": context,
            "user_stats": user_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/report', methods=['GET'])
@login_required
def api_ai_monthly_report():
    """API para relatório mensal gerado por IA"""
    try:
        # Dados do mês atual
        current_month = datetime.now().replace(day=1)
        
        monthly_records = FuelRecord.query.join(Vehicle).filter(
            Vehicle.user_id == current_user.id,
            FuelRecord.date >= current_month.date()
        ).all()
        
        if not monthly_records:
            return jsonify({"error": "Nenhum dado encontrado para este mês"})
        
        # Preparar dados mensais
        monthly_data = {
            "period": current_month.strftime("%Y-%m"),
            "total_records": len(monthly_records),
            "total_spent": sum(float(r.total_cost) for r in monthly_records),
            "total_liters": sum(float(r.liters) for r in monthly_records),
            "fuel_distribution": {},
            "stations_used": [],
            "average_price": 0
        }
        
        # Distribuição por combustível
        fuel_types = {}
        stations = set()
        
        for record in monthly_records:
            fuel_types[record.fuel_type] = fuel_types.get(record.fuel_type, 0) + float(record.liters)
            if record.gas_station:
                stations.add(record.gas_station)
        
        monthly_data["fuel_distribution"] = fuel_types
        monthly_data["stations_used"] = list(stations)
        monthly_data["average_price"] = monthly_data["total_spent"] / monthly_data["total_liters"] if monthly_data["total_liters"] > 0 else 0
        
        # Chamar IA para gerar relatório
        report = ai_service.generate_monthly_report(monthly_data, current_user.username)
        
        return jsonify({
            "report": report,
            "data": monthly_data,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/regional', methods=['GET'])
@login_required
def api_ai_regional_analysis():
    """API para análise comparativa regional com IA"""
    try:
        # Coletar dados do usuário dos últimos 6 meses para análise regional
        six_months_ago = datetime.now() - timedelta(days=180)
        records = FuelRecord.query.join(Vehicle).filter(
            Vehicle.user_id == current_user.id,
            FuelRecord.date >= six_months_ago.date()
        ).order_by(FuelRecord.date.desc()).all()
        
        if not records:
            return jsonify({"error": "Dados insuficientes para análise regional"})
        
        # Preparar dados regionais
        regional_data = {
            "total_records": len(records),
            "period_months": 6,
            "user_region": request.args.get('region', 'Brasil'),
            "average_price_per_liter": sum(float(r.price_per_liter) for r in records) / len(records),
            "total_spent": sum(float(r.total_cost) for r in records),
            "total_liters": sum(float(r.liters) for r in records),
            "fuel_types_used": list(set(r.fuel_type for r in records)),
            "stations_diversity": len(set(r.gas_station for r in records if r.gas_station)),
            "monthly_averages": {},
            "price_trends": []
        }
        
        # Calcular médias mensais
        monthly_data = {}
        for record in records:
            month_key = record.date.strftime("%Y-%m")
            if month_key not in monthly_data:
                monthly_data[month_key] = {"total_cost": 0, "total_liters": 0, "count": 0}
            monthly_data[month_key]["total_cost"] += float(record.total_cost)
            monthly_data[month_key]["total_liters"] += float(record.liters)
            monthly_data[month_key]["count"] += 1
        
        for month, data in monthly_data.items():
            regional_data["monthly_averages"][month] = {
                "avg_price": data["total_cost"] / data["total_liters"] if data["total_liters"] > 0 else 0,
                "total_spent": data["total_cost"],
                "records_count": data["count"]
            }
        
        # Chamar IA para análise regional
        user_region = request.args.get('region', 'Brasil')
        analysis = ai_service.regional_comparative_analysis(regional_data, user_region)
        
        return jsonify({
            "regional_analysis": analysis,
            "user_data": regional_data,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === APIS PARA GRÁFICOS ===

@app.route('/api/monthly_data', methods=['GET'])
@login_required
def api_monthly_data():
    """API para dados dos gráficos mensais"""
    try:
        # Parâmetros de filtro
        vehicle_id = request.args.get('vehicle_id', type=int)
        days = request.args.get('days', type=int)
        
        # Query base
        query = FuelRecord.query.join(Vehicle).filter(Vehicle.user_id == current_user.id)
        
        # Aplicar filtros
        if vehicle_id:
            query = query.filter(Vehicle.id == vehicle_id)
        
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            query = query.filter(FuelRecord.date >= cutoff_date.date())
        
        records = query.order_by(FuelRecord.date.desc()).all()
        
        # Agrupar por mês
        monthly_data = {}
        for record in records:
            month_key = record.date.strftime("%Y-%m")
            if month_key not in monthly_data:
                monthly_data[month_key] = 0
            monthly_data[month_key] += float(record.total_cost)
        
        # Converter para formato do gráfico (últimos 12 meses)
        from datetime import datetime
        import calendar
        
        current_date = datetime.now()
        labels = []
        data = []
        
        for i in range(11, -1, -1):  # Últimos 12 meses
            # Calcular mês correto subtraindo meses
            year = current_date.year
            month = current_date.month - i
            
            while month <= 0:
                month += 12
                year -= 1
                
            month_date = datetime(year, month, 1)
            month_key = month_date.strftime("%Y-%m")
            month_label = f"{calendar.month_abbr[month_date.month]}/{month_date.year}"
            
            labels.append(month_label)
            data.append(monthly_data.get(month_key, 0))
        
        return jsonify({
            "labels": labels,
            "data": data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/fuel_distribution', methods=['GET'])
@login_required
def api_fuel_distribution():
    """API para dados de distribuição de combustível"""
    try:
        # Parâmetros de filtro
        vehicle_id = request.args.get('vehicle_id', type=int)
        days = request.args.get('days', type=int)
        
        # Query base
        query = FuelRecord.query.join(Vehicle).filter(Vehicle.user_id == current_user.id)
        
        # Aplicar filtros
        if vehicle_id:
            query = query.filter(Vehicle.id == vehicle_id)
        
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            query = query.filter(FuelRecord.date >= cutoff_date.date())
        
        records = query.all()
        
        # Contar por tipo de combustível
        fuel_distribution = {}
        for record in records:
            fuel_type = record.fuel_type
            # Traduzir nomes dos combustíveis
            fuel_names = {
                'gasoline': 'Gasolina',
                'ethanol': 'Etanol', 
                'diesel': 'Diesel',
                'gas': 'GNV'
            }
            fuel_display = fuel_names.get(fuel_type, fuel_type.title())
            
            if fuel_display not in fuel_distribution:
                fuel_distribution[fuel_display] = 0
            fuel_distribution[fuel_display] += float(record.liters)
        
        return jsonify(fuel_distribution)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === TRATAMENTO DE ERROS ===

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# === INICIALIZACAO ===

def create_tables():
    """Criar tabelas do banco de dados"""
    try:
        with app.app_context():
            db.create_all()
            print("Tabelas criadas com sucesso!")
            
            # Migrar dados de OilChange para MaintenanceRecord se necessário
            migrate_oil_records_to_maintenance()
            
    except Exception as e:
        print(f"Erro ao criar tabelas: {e}")

def migrate_oil_records_to_maintenance():
    """Migra registros de OilChange para MaintenanceRecord"""
    try:
        # Verificar se já existem registros migrados
        existing_oil_maintenance = MaintenanceRecord.query.filter_by(maintenance_type='oil').first()
        if existing_oil_maintenance:
            print("Dados de óleo já migrados para MaintenanceRecord")
            return
        
        # Buscar todos os registros de OilChange
        oil_changes = OilChange.query.all()
        
        if not oil_changes:
            print("Nenhum registro de OilChange para migrar")
            return
        
        migrated_count = 0
        for oil_change in oil_changes:
            # Criar novo registro de manutenção
            maintenance_record = MaintenanceRecord(
                vehicle_id=oil_change.vehicle_id,
                date=oil_change.date,
                maintenance_type='oil',
                description=f"Troca de óleo migrada - {oil_change.notes or 'Sem observações'}",
                km_at_service=oil_change.km_at_change,
                service_interval_km=oil_change.interval_km,
                service_interval_months=oil_change.interval_months,
                notes=f"Migrado de OilChange em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. Notas originais: {oil_change.notes or 'Nenhuma'}",
                created_at=oil_change.created_at,
                created_by_voice=False
            )
            
            # Calcular próximo serviço automaticamente
            maintenance_record.calculate_next_service()
            
            db.session.add(maintenance_record)
            migrated_count += 1
        
        db.session.commit()
        print(f"✅ {migrated_count} registros de óleo migrados para MaintenanceRecord")
        
        # OPCIONAL: Manter tabela OilChange para compatibilidade, mas com aviso
        print("💡 Tabela OilChange mantida para compatibilidade. Use MaintenanceRecord para novos registros.")
        
    except Exception as e:
        print(f"Erro na migração de dados de óleo: {e}")
        db.session.rollback()

# === ENDPOINT DE RECONHECIMENTO DE VOZ ===

@app.route('/api/ai/voice-command', methods=['POST'])
@login_required
def api_voice_command():
    """API para processar comandos de voz e extrair dados estruturados"""
    try:
        data = request.get_json()
        transcript = data.get('transcript', '').strip()
        
        if not transcript:
            return jsonify({
                "success": False,
                "message": "Nenhum texto foi fornecido"
            })
        
        # Processar comando com IA
        result = ai_service.process_voice_command(transcript, current_user.id)
        
        if not result:
            return jsonify({
                "success": False, 
                "message": "Erro ao processar comando. Tente novamente."
            })
        
        # Processar ação sugerida
        if result['acao_sugerida'] == 'salvar_abastecimento':
            success = process_fuel_record_from_voice(result['dados_extraidos'], current_user.id)
            return jsonify({
                "success": success,
                "message": result['mensagem_usuario'],
                "data": result['dados_extraidos'] if success else None,
                "data_saved": success
            })
            
        elif result['acao_sugerida'] == 'salvar_manutencao':
            success, message, maintenance_record = process_maintenance_record_from_voice(
                result['dados_extraidos'], current_user.id
            )
            return jsonify({
                "success": success,
                "message": message,
                "data": result['dados_extraidos'] if success else None,
                "data_saved": success
            })
            
        elif result['acao_sugerida'] == 'responder_consulta':
            # TODO: Implementar respostas a consultas
            return jsonify({
                "success": True,
                "message": "Consulta processada: " + result['mensagem_usuario']
            })
            
        else:  # pedir_esclarecimento ou desconhecido
            return jsonify({
                "success": False,
                "message": result['mensagem_usuario'] + " Por favor, seja mais específico."
            })
        
    except Exception as e:
        print(f"Erro no endpoint de comando de voz: {e}")
        return jsonify({
            "success": False,
            "message": "Erro interno. Tente novamente."
        }), 500


def process_fuel_record_from_voice(dados, user_id):
    """Helper para salvar registro de combustível extraído da voz"""
    try:
        # Validar dados mínimos necessários
        if not dados.get('valor') or not dados.get('tipo_combustivel'):
            return False
        
        # Obter veículo padrão do usuário (primeiro veículo)
        vehicle = Vehicle.query.filter_by(user_id=user_id).first()
        if not vehicle:
            return False
        
        # Processar data
        data_abastecimento = datetime.now().date()
        if dados.get('data') == 'hoje':
            data_abastecimento = datetime.now().date()
        elif dados.get('data') == 'ontem':
            data_abastecimento = (datetime.now() - timedelta(days=1)).date()
        elif dados.get('data') == 'anteontem':
            data_abastecimento = (datetime.now() - timedelta(days=2)).date()
        # TODO: Processar outras datas formato YYYY-MM-DD
        
        # Calcular litros se não fornecido (assumir preço médio)
        litros = dados.get('litros')
        if not litros and dados.get('valor'):
            # Preço médio estimado por tipo de combustível
            precos_medios = {
                'gasolina': 5.50,
                'etanol': 3.80,  
                'diesel': 5.80,
                'gnv': 4.20
            }
            preco_estimado = precos_medios.get(dados.get('tipo_combustivel'), 5.50)
            litros = dados['valor'] / preco_estimado
        
        # Calcular preço por litro
        preco_por_litro = dados['valor'] / litros if litros else 5.50
        
        # Criar registro
        fuel_record = FuelRecord(
            vehicle_id=vehicle.id,
            date=data_abastecimento,
            fuel_type=dados['tipo_combustivel'],
            liters=round(litros, 2) if litros else 0,
            price_per_liter=round(preco_por_litro, 3),
            total_cost=round(dados['valor'], 2),
            gas_station=dados.get('posto', 'Não informado'),
            odometer_reading=dados.get('quilometragem'),
            notes=f"Criado por comando de voz: {dados.get('descricao', '')}"
        )
        
        db.session.add(fuel_record)
        db.session.commit()
        return True
        
    except Exception as e:
        print(f"Erro ao salvar registro de voz: {e}")
        db.session.rollback()
        return False


# Para desenvolvimento local
if __name__ == '__main__':
    create_tables()
    
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)

# Para Vercel - criar tabelas apenas se necessário
else:
    try:
        with app.app_context():
            # Verificar se as tabelas existem
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if not inspector.has_table('users'):
                create_tables()
    except Exception as e:
        print(f"Erro na inicialização: {e}")
