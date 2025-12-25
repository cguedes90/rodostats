# FuelTracker Pro - Controle Inteligente de Combustível
# Desenvolvido por InovaMente Labs

import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import re
import json
import base64
import io
import csv
from PIL import Image
import pytesseract
import google.generativeai as genai

# Configurar Tesseract
try:
    from tesseract_config import configure_tesseract
    configure_tesseract()
except ImportError:
    print("Arquivo tesseract_config.py não encontrado. OCR pode não funcionar.")
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

# Configuração inicial
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://neondb_owner:npg_ArdO9L4sGxUD@ep-sweet-shape-ac6v4rp3-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Proxy fix para produção
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configurações de serviços externos
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Modelos de dados
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255))
    oauth_photo = db.Column(db.String(500))
    profile_photo = db.Column(db.String(255))
    provider = db.Column(db.String(50), default='local')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    vehicles = db.relationship('Vehicle', backref='owner', lazy=True, cascade='all, delete-orphan')
    fuel_records = db.relationship('FuelRecord', backref='user', lazy=True, cascade='all, delete-orphan')

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    license_plate = db.Column(db.String(10), nullable=False)
    color = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    fuel_records = db.relationship('FuelRecord', backref='vehicle', lazy=True, cascade='all, delete-orphan')

class FuelRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    liters = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    fuel_type = db.Column(db.String(20), nullable=False)
    odometer = db.Column(db.Integer)
    gas_station = db.Column(db.String(100))
    full_tank = db.Column(db.Boolean, default=True)
    fuel_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Utilitários
def validate_license_plate(plate):
    """Valida placa brasileira (formato antigo ABC-1234 ou Mercosul ABC1D23)"""
    old_format = re.match(r'^[A-Z]{3}-?\d{4}$', plate.upper())
    mercosul_format = re.match(r'^[A-Z]{3}\d[A-Z]\d{2}$', plate.upper())
    return old_format or mercosul_format

def send_welcome_email(user_email, user_name):
    """Envia email de boas-vindas usando SendGrid"""
    if not SENDGRID_API_KEY:
        return False
    
    try:
        message = Mail(
            from_email='noreply@fueltrackerpro.com',
            to_emails=user_email,
            subject='Bem-vindo ao FuelTracker Pro! 🚗',
            html_content=f'''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #4A90E2, #28C997); padding: 40px; text-align: center; color: white;">
                    <h1>🚗 FuelTracker Pro</h1>
                    <p>Controle Inteligente de Combustível</p>
                </div>
                <div style="padding: 30px; background: #f8f9fa;">
                    <h2>Olá, {user_name}! 👋</h2>
                    <p>Seja bem-vindo ao FuelTracker Pro! Agora você pode:</p>
                    <ul>
                        <li>📊 Acompanhar seus gastos com combustível</li>
                        <li>🤖 Processar recibos automaticamente com IA</li>
                        <li>📱 Usar nossa app PWA no seu celular</li>
                        <li>📈 Visualizar análises detalhadas de consumo</li>
                    </ul>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="https://fueltrackerpro.com/dashboard" 
                           style="background: linear-gradient(135deg, #4A90E2, #28C997); 
                                  color: white; padding: 15px 30px; text-decoration: none; 
                                  border-radius: 5px; display: inline-block;">
                            Começar Agora
                        </a>
                    </div>
                </div>
                <div style="text-align: center; padding: 20px; color: #666;">
                    <p>Desenvolvido com ❤️ por InovaMente Labs</p>
                </div>
            </div>
            '''
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        return False

def process_receipt_with_ai(image_data):
    """Processa recibo usando Google Gemini AI"""
    if not GEMINI_API_KEY:
        return None
    
    try:
        # Primeiro, tenta OCR tradicional
        image = Image.open(io.BytesIO(image_data))
        text = pytesseract.image_to_string(image, lang='por')
        
        # Depois processa com Gemini
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""
        Analise este texto extraído de um recibo de posto de gasolina brasileiro e extraia as seguintes informações:
        
        Texto do recibo:
        {text}
        
        Extraia APENAS as seguintes informações e retorne em formato JSON:
        {{
            "liters": float ou null,
            "total_cost": float ou null,
            "fuel_type": "Gasolina Comum" ou "Etanol" ou "Diesel" ou null,
            "gas_station": string ou null,
            "unit_price": float ou null
        }}
        
        Regras:
        - liters: quantidade em litros (ex: 45.5)
        - total_cost: valor total pago (ex: 280.50)
        - fuel_type: tipo de combustível
        - gas_station: nome do posto
        - unit_price: preço por litro
        
        Se não conseguir identificar algum valor, retorne null para esse campo.
        """
        
        response = model.generate_content(prompt)
        result = json.loads(response.text.strip())
        return result
        
    except Exception as e:
        print(f"Erro no processamento AI: {e}")
        return None

def calculate_consumption_metrics(user_id, vehicle_id=None, days=None):
    """Calcula métricas de consumo e quilometragem"""
    query = FuelRecord.query.filter_by(user_id=user_id)
    
    if vehicle_id:
        query = query.filter_by(vehicle_id=vehicle_id)
    
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(FuelRecord.fuel_date >= cutoff_date)
    
    # Ordena por data e filtra registros com odômetro
    records = query.filter(FuelRecord.odometer.isnot(None)).order_by(FuelRecord.fuel_date).all()
    
    if len(records) < 2:
        return {
            'total_km': 0,
            'average_consumption': 0,
            'best_consumption': 0,
            'worst_consumption': 0,
            'km_last_30_days': 0
        }
    
    # Calcula distâncias entre abastecimentos
    consumptions = []
    total_km = 0
    
    for i in range(1, len(records)):
        prev_record = records[i-1]
        curr_record = records[i]
        
        km_traveled = curr_record.odometer - prev_record.odometer
        
        # Filtros de dados irreais
        if km_traveled > 0 and km_traveled <= 2000:
            consumption = km_traveled / prev_record.liters
            
            # Filtro de consumo realista (1-30 km/L)
            if 1 <= consumption <= 30:
                consumptions.append({
                    'km': km_traveled,
                    'consumption': consumption,
                    'liters': prev_record.liters,
                    'date': curr_record.fuel_date
                })
                total_km += km_traveled
    
    if not consumptions:
        return {
            'total_km': 0,
            'average_consumption': 0,
            'best_consumption': 0,
            'worst_consumption': 0,
            'km_last_30_days': 0
        }
    
    # Calcula consumo médio ponderado pela distância
    total_weighted_consumption = sum(c['km'] * c['consumption'] for c in consumptions)
    average_consumption = total_weighted_consumption / total_km
    
    # Melhor e pior consumo
    consumption_values = [c['consumption'] for c in consumptions]
    best_consumption = max(consumption_values)
    worst_consumption = min(consumption_values)
    
    # Km dos últimos 30 dias
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    km_last_30_days = sum(
        c['km'] for c in consumptions 
        if c['date'] >= thirty_days_ago
    )
    
    return {
        'total_km': total_km,
        'average_consumption': round(average_consumption, 2),
        'best_consumption': round(best_consumption, 2),
        'worst_consumption': round(worst_consumption, 2),
        'km_last_30_days': km_last_30_days
    }

# Rotas principais
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        # Verifica se usuário já existe
        if User.query.filter_by(email=email).first():
            flash('Email já cadastrado!', 'error')
            return render_template('register.html')
        
        # Cria novo usuário
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            provider='local'
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Envia email de boas-vindas
        send_welcome_email(email, name)
        
        flash('Cadastro realizado com sucesso!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou senha inválidos!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Parâmetros de filtro
    vehicle_id = request.args.get('vehicle_id', type=int)
    days = request.args.get('days', type=int)
    
    # Query base
    query = FuelRecord.query.filter_by(user_id=current_user.id)
    
    if vehicle_id:
        query = query.filter_by(vehicle_id=vehicle_id)
    
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(FuelRecord.fuel_date >= cutoff_date)
    
    records = query.order_by(FuelRecord.fuel_date.desc()).all()
    
    # Métricas básicas
    total_spent = sum(r.total_cost for r in records)
    total_liters = sum(r.liters for r in records)
    avg_price = total_spent / total_liters if total_liters > 0 else 0
    
    # Posto favorito
    stations = {}
    for record in records:
        if record.gas_station:
            stations[record.gas_station] = stations.get(record.gas_station, 0) + 1
    favorite_station = max(stations.items(), key=lambda x: x[1])[0] if stations else "N/A"
    
    # Métricas de consumo
    consumption_metrics = calculate_consumption_metrics(current_user.id, vehicle_id, days)
    
    # Dados para gráficos
    monthly_data = {}
    fuel_distribution = {'Gasolina Comum': 0, 'Etanol': 0, 'Diesel': 0}
    
    for record in records:
        month_key = record.fuel_date.strftime('%Y-%m')
        monthly_data[month_key] = monthly_data.get(month_key, 0) + record.total_cost
        fuel_distribution[record.fuel_type] = fuel_distribution.get(record.fuel_type, 0) + record.liters
    
    vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    
    return render_template('dashboard.html',
                         records=records,
                         vehicles=vehicles,
                         total_spent=total_spent,
                         total_liters=total_liters,
                         avg_price=avg_price,
                         favorite_station=favorite_station,
                         consumption_metrics=consumption_metrics,
                         monthly_data=monthly_data,
                         fuel_distribution=fuel_distribution,
                         selected_vehicle=vehicle_id,
                         selected_days=days)

@app.route('/vehicles')
@login_required
def vehicles():
    user_vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    return render_template('vehicles.html', vehicles=user_vehicles)

@app.route('/add_vehicle', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if request.method == 'POST':
        brand = request.form['brand']
        model = request.form['model']
        year = int(request.form['year'])
        license_plate = request.form['license_plate'].upper()
        color = request.form['color']
        
        # Validação da placa
        if not validate_license_plate(license_plate):
            flash('Formato de placa inválido!', 'error')
            return render_template('add_vehicle.html')
        
        vehicle = Vehicle(
            user_id=current_user.id,
            brand=brand,
            model=model,
            year=year,
            license_plate=license_plate,
            color=color
        )
        
        db.session.add(vehicle)
        db.session.commit()
        
        flash('Veículo adicionado com sucesso!', 'success')
        return redirect(url_for('vehicles'))
    
    return render_template('add_vehicle.html')

@app.route('/add_fuel', methods=['GET', 'POST'])
@login_required
def add_fuel():
    if request.method == 'POST':
        vehicle_id = int(request.form['vehicle_id'])
        liters = float(request.form['liters'])
        total_cost = float(request.form['total_cost'])
        fuel_type = request.form['fuel_type']
        odometer = request.form.get('odometer')
        gas_station = request.form.get('gas_station', '')
        full_tank = 'full_tank' in request.form
        
        fuel_record = FuelRecord(
            user_id=current_user.id,
            vehicle_id=vehicle_id,
            liters=liters,
            total_cost=total_cost,
            fuel_type=fuel_type,
            odometer=int(odometer) if odometer else None,
            gas_station=gas_station,
            full_tank=full_tank
        )
        
        db.session.add(fuel_record)
        db.session.commit()
        
        flash('Abastecimento registrado com sucesso!', 'success')
        return redirect(url_for('dashboard'))
    
    vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    return render_template('add_fuel.html', vehicles=vehicles)

@app.route('/process_receipt', methods=['POST'])
@login_required
def process_receipt():
    if 'receipt_image' not in request.files:
        return jsonify({'error': 'Nenhuma imagem enviada'}), 400
    
    file = request.files['receipt_image']
    if file.filename == '':
        return jsonify({'error': 'Nenhuma imagem selecionada'}), 400
    
    try:
        image_data = file.read()
        result = process_receipt_with_ai(image_data)
        
        if result:
            return jsonify(result)
        else:
            return jsonify({'error': 'Não foi possível processar o recibo'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Erro no processamento: {str(e)}'}), 500

@app.route('/history')
@login_required
def history():
    # Aplicar mesmos filtros do dashboard
    vehicle_id = request.args.get('vehicle_id', type=int)
    days = request.args.get('days', type=int)
    
    query = FuelRecord.query.filter_by(user_id=current_user.id)
    
    if vehicle_id:
        query = query.filter_by(vehicle_id=vehicle_id)
    
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(FuelRecord.fuel_date >= cutoff_date)
    
    records = query.order_by(FuelRecord.fuel_date.desc()).all()
    vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    
    return render_template('history.html', 
                         records=records, 
                         vehicles=vehicles,
                         selected_vehicle=vehicle_id,
                         selected_days=days)

@app.route('/update_odometer', methods=['POST'])
@login_required
def update_odometer():
    try:
        record_id = int(request.json['record_id'])
        new_odometer = request.json['odometer']
        
        record = FuelRecord.query.get_or_404(record_id)
        
        # Verifica se o usuário é dono do registro
        if record.user_id != current_user.id:
            return jsonify({'error': 'Acesso negado'}), 403
        
        record.odometer = int(new_odometer) if new_odometer else None
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/upload_profile_photo', methods=['POST'])
@login_required
def upload_profile_photo():
    if 'profile_photo' not in request.files:
        flash('Nenhuma imagem selecionada!', 'error')
        return redirect(url_for('profile'))
    
    file = request.files['profile_photo']
    if file.filename == '':
        flash('Nenhuma imagem selecionada!', 'error')
        return redirect(url_for('profile'))
    
    if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        filename = secure_filename(f"profile_{current_user.id}_{datetime.utcnow().timestamp()}.jpg")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Cria diretório se não existir
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Processa e salva imagem
        image = Image.open(file)
        image = image.convert('RGB')
        image.thumbnail((200, 200), Image.Resampling.LANCZOS)
        image.save(filepath, 'JPEG', quality=85)
        
        current_user.profile_photo = filename
        db.session.commit()
        
        flash('Foto atualizada com sucesso!', 'success')
    else:
        flash('Formato de arquivo inválido! Use PNG, JPG ou JPEG.', 'error')
    
    return redirect(url_for('profile'))

@app.route('/export_csv')
@login_required
def export_csv():
    # Aplicar filtros
    vehicle_id = request.args.get('vehicle_id', type=int)
    days = request.args.get('days', type=int)
    
    query = FuelRecord.query.filter_by(user_id=current_user.id)
    
    if vehicle_id:
        query = query.filter_by(vehicle_id=vehicle_id)
    
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(FuelRecord.fuel_date >= cutoff_date)
    
    records = query.order_by(FuelRecord.fuel_date.desc()).all()
    
    # Criar CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Cabeçalhos
    writer.writerow([
        'Data', 'Veículo', 'Combustível', 'Litros', 'Valor Total', 
        'Preço/Litro', 'Quilometragem', 'Posto', 'Tanque Cheio'
    ])
    
    # Dados
    for record in records:
        vehicle = Vehicle.query.get(record.vehicle_id)
        price_per_liter = record.total_cost / record.liters
        
        writer.writerow([
            record.fuel_date.strftime('%d/%m/%Y %H:%M'),
            f"{vehicle.brand} {vehicle.model} ({vehicle.license_plate})",
            record.fuel_type,
            f"{record.liters:.2f}",
            f"R$ {record.total_cost:.2f}",
            f"R$ {price_per_liter:.3f}",
            record.odometer or '',
            record.gas_station or '',
            'Sim' if record.full_tank else 'Não'
        ])
    
    output.seek(0)
    
    # Criar resposta
    response = app.response_class(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=fueltracker_export_{datetime.now().strftime("%Y%m%d")}.csv'}
    )
    
    return response

@app.route('/export_pdf')
@login_required
def export_pdf():
    # Similar ao CSV, mas gera PDF com reportlab
    # Por brevidade, implementação simplificada
    flash('Exportação PDF em desenvolvimento!', 'info')
    return redirect(url_for('dashboard'))

# API endpoints para gráficos
@app.route('/api/monthly_data')
@login_required
def api_monthly_data():
    vehicle_id = request.args.get('vehicle_id', type=int)
    days = request.args.get('days', type=int)
    
    query = FuelRecord.query.filter_by(user_id=current_user.id)
    
    if vehicle_id:
        query = query.filter_by(vehicle_id=vehicle_id)
    
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(FuelRecord.fuel_date >= cutoff_date)
    
    records = query.all()
    
    monthly_data = {}
    for record in records:
        month_key = record.fuel_date.strftime('%Y-%m')
        monthly_data[month_key] = monthly_data.get(month_key, 0) + record.total_cost
    
    return jsonify(monthly_data)

@app.route('/api/fuel_distribution')
@login_required
def api_fuel_distribution():
    vehicle_id = request.args.get('vehicle_id', type=int)
    days = request.args.get('days', type=int)
    
    query = FuelRecord.query.filter_by(user_id=current_user.id)
    
    if vehicle_id:
        query = query.filter_by(vehicle_id=vehicle_id)
    
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(FuelRecord.fuel_date >= cutoff_date)
    
    records = query.all()
    
    fuel_distribution = {}
    for record in records:
        fuel_distribution[record.fuel_type] = fuel_distribution.get(record.fuel_type, 0) + record.liters
    
    return jsonify(fuel_distribution)

# PWA routes
@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "FuelTracker Pro",
        "short_name": "FuelTracker",
        "description": "Controle Inteligente de Combustível",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1a1a1a",
        "theme_color": "#4A90E2",
        "icons": [
            {
                "src": "/static/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js')

# Inicialização da aplicação
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
