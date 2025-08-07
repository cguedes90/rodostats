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
try:
    from PIL import Image
except ImportError:
    Image = None
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Configuracao inicial
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://neondb_owner:npg_ArdO9L4sGxUD@ep-sweet-shape-ac6v4rp3-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Proxy fix para producao
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Banco de dados
db = SQLAlchemy(app)

# Configuração do Flask-Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@rodostats.com')

mail = Mail(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para acessar esta página.'

# Configurar Google Gemini AI
if genai:
    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)

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

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    license_plate = db.Column(db.String(20), unique=True, nullable=False)
    fuel_type = db.Column(db.String(20), nullable=False, default='gasoline')
    tank_capacity = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    fuel_records = db.relationship('FuelRecord', backref='vehicle', lazy=True, cascade='all, delete-orphan')
    
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# === FUNCOES AUXILIARES ===

def allowed_file(filename):
    """Verifica se o arquivo e uma imagem permitida"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_receipt_with_ai(image_path):
    """Processa nota fiscal com Google Gemini AI"""
    if not genai or not os.environ.get('GEMINI_API_KEY'):
        return None
    
    try:
        # Configurar o modelo
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Ler a imagem
        if Image:
            image = Image.open(image_path)
        else:
            return None
        
        prompt = """
        Analise esta nota fiscal de posto de combustivel e extraia as seguintes informacoes em formato JSON:
        
        {
            "data": "YYYY-MM-DD",
            "posto": "Nome do posto",
            "combustivel": "tipo do combustivel (gasolina/etanol/diesel)",
            "litros": 0.0,
            "preco_litro": 0.0,
            "total": 0.0,
            "observacoes": "informacoes adicionais"
        }
        
        Se nao conseguir extrair alguma informacao, use null para esse campo.
        Responda APENAS com o JSON, sem texto adicional.
        """
        
        response = model.generate_content([prompt, image])
        
        if response.text:
            # Limpar a resposta e extrair JSON
            json_text = response.text.strip()
            if json_text.startswith('```json'):
                json_text = json_text[7:]
            if json_text.endswith('```'):
                json_text = json_text[:-3]
            
            try:
                return json.loads(json_text.strip())
            except json.JSONDecodeError:
                return None
        
    except Exception as e:
        print(f"Erro no processamento da IA: {e}")
        return None

def calculate_fuel_efficiency(vehicle_id):
    """Calcula eficiencia de combustivel"""
    records = FuelRecord.query.filter_by(vehicle_id=vehicle_id).order_by(FuelRecord.date).all()
    
    if len(records) < 2:
        return {
            'average_consumption': 0,
            'best_consumption': 0,
            'worst_consumption': 0,
            'trend': 'stable'
        }
    
    consumptions = []
    for i in range(1, len(records)):
        distance = records[i].odometer - records[i-1].odometer
        fuel = records[i].liters
        
        if distance > 0 and fuel > 0:
            consumption = distance / fuel
            consumptions.append(consumption)
    
    if not consumptions:
        return {
            'average_consumption': 0,
            'best_consumption': 0,
            'worst_consumption': 0,
            'trend': 'stable'
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
        'trend': trend
    }

# === ROTAS ===

@app.route('/')
def index():
    """Pagina inicial"""
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login do usuario"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        print(f"[LOGIN] Tentativa de login para usuário: {username}")
        
        user = User.query.filter_by(username=username).first()
        print(f"[LOGIN] Usuário encontrado: {user is not None}")
        
        if user and user.check_password(password):
            print(f"[LOGIN] Senha correta para {username}")
            login_user(user)
            next_page = request.args.get('next')
            print(f"[LOGIN] Redirecionando para: {next_page or 'dashboard'}")
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

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal"""
    print(f"[DASHBOARD] Usuário atual: {current_user.username}")
    
    vehicles = Vehicle.query.filter_by(user_id=current_user.id, is_active=True).all()
    print(f"[DASHBOARD] Veículos encontrados: {len(vehicles)}")
    
    # Estatisticas gerais
    total_vehicles = len(vehicles)
    total_records = FuelRecord.query.join(Vehicle).filter(Vehicle.user_id == current_user.id).count()
    
    # Ultimos abastecimentos
    recent_records = FuelRecord.query.join(Vehicle).filter(
        Vehicle.user_id == current_user.id
    ).order_by(FuelRecord.date.desc()).limit(5).all()
    
    # Gastos do mes atual
    current_month = datetime.now().replace(day=1)
    monthly_expense = db.session.query(db.func.sum(FuelRecord.total_cost)).join(Vehicle).filter(
        Vehicle.user_id == current_user.id,
        FuelRecord.date >= current_month
    ).scalar() or 0
    
    # Preparar dados para graficos
    chart_data = []
    for vehicle in vehicles:
        records = FuelRecord.query.filter_by(vehicle_id=vehicle.id).order_by(FuelRecord.date).all()
        if records:
            chart_data.append({
                'vehicle': vehicle.name,
                'data': [{'date': r.date.strftime('%Y-%m-%d'), 'consumption': r.consumption()} for r in records if r.consumption() > 0]
            })
    
    print(f"[DASHBOARD] Renderizando template dashboard.html")
    
    return render_template('dashboard.html', 
                         vehicles=vehicles,
                         total_vehicles=total_vehicles,
                         total_records=total_records,
                         recent_records=recent_records,
                         monthly_expense=monthly_expense,
                         chart_data=chart_data)

@app.route('/vehicles')
@login_required
def vehicles():
    """Lista de veiculos"""
    vehicles = Vehicle.query.filter_by(user_id=current_user.id, is_active=True).all()
    return render_template('vehicles.html', vehicles=vehicles)

@app.route('/add_vehicle', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    """Adicionar novo veiculo"""
    if request.method == 'POST':
        vehicle = Vehicle(
            user_id=current_user.id,
            name=request.form['name'],
            brand=request.form['brand'],
            model=request.form['model'],
            year=int(request.form['year']),
            license_plate=request.form['license_plate'].upper(),
            fuel_type=request.form['fuel_type'],
            tank_capacity=float(request.form['tank_capacity'])
        )
        
        db.session.add(vehicle)
        db.session.commit()
        
        flash('Veiculo adicionado com sucesso!', 'success')
        return redirect(url_for('vehicles'))
    
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
    
    return render_template('vehicle_detail.html', 
                         vehicle=vehicle, 
                         records=records, 
                         efficiency=efficiency,
                         recent_expense=recent_expense)

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
    
    return render_template('add_fuel_record.html', vehicle=vehicle)

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
    with app.app_context():
        db.create_all()
        print("Tabelas criadas com sucesso!")

if __name__ == '__main__':
    create_tables()
    
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
