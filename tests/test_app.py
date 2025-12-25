# -*- coding: utf-8 -*-
"""
Testes Automatizados - RodoStats
Testes básicos de funcionalidade da aplicação
"""

import pytest
import os
import sys

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configurar variáveis de ambiente para teste
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key-for-testing-only'
os.environ['FLASK_ENV'] = 'testing'

from app import app, db

@pytest.fixture
def client():
    """Fixture para criar cliente de teste"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()


class TestSecurityConfig:
    """Testes de configuração de segurança"""

    def test_no_hardcoded_credentials(self):
        """Verifica se não há credenciais hardcoded no código"""
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # Verificar se não há URLs de banco hardcoded
        assert 'postgresql://' not in content or 'os.environ.get' in content
        assert 'npg_' not in content  # Prefixo de senha do Neon

    def test_env_variables_required(self):
        """Verifica se variáveis de ambiente são obrigatórias"""
        # Remover variáveis temporariamente
        old_db = os.environ.pop('DATABASE_URL', None)
        old_secret = os.environ.pop('SESSION_SECRET', None)

        try:
            # Tentar importar app sem variáveis deve falhar
            with pytest.raises(ValueError):
                import importlib
                importlib.reload(sys.modules['app'])
        finally:
            # Restaurar variáveis
            if old_db:
                os.environ['DATABASE_URL'] = old_db
            if old_secret:
                os.environ['SESSION_SECRET'] = old_secret


class TestRoutesPublic:
    """Testes de rotas públicas (não autenticadas)"""

    def test_index_redirect(self, client):
        """Testa se rota principal redireciona para login"""
        response = client.get('/')
        assert response.status_code == 302  # Redirect

    def test_login_page_loads(self, client):
        """Testa se página de login carrega"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Login' in response.data or b'Entrar' in response.data

    def test_register_page_loads(self, client):
        """Testa se página de registro carrega"""
        response = client.get('/register')
        assert response.status_code == 200
        assert b'Cadastr' in response.data or b'Registr' in response.data


class TestRoutesProtected:
    """Testes de rotas protegidas (requerem autenticação)"""

    def test_dashboard_requires_login(self, client):
        """Testa se dashboard requer login"""
        response = client.get('/dashboard')
        assert response.status_code == 302  # Redirect para login

    def test_vehicles_requires_login(self, client):
        """Testa se página de veículos requer login"""
        response = client.get('/vehicles')
        assert response.status_code == 302  # Redirect para login

    def test_analytics_requires_login(self, client):
        """Testa se analytics requer login"""
        response = client.get('/analytics')
        assert response.status_code == 302  # Redirect para login


class TestUserRegistration:
    """Testes de registro de usuário"""

    def test_register_new_user(self, client):
        """Testa registro de novo usuário"""
        response = client.post('/register', data={
            'name': 'Test User',
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
            'terms': 'on'
        }, follow_redirects=True)

        # Deve redirecionar para login ou dashboard
        assert response.status_code == 200

    def test_register_duplicate_email(self, client):
        """Testa se não permite email duplicado"""
        # Primeiro registro
        client.post('/register', data={
            'name': 'User One',
            'username': 'user1',
            'email': 'duplicate@example.com',
            'password': 'Pass123!',
            'confirm_password': 'Pass123!',
            'terms': 'on'
        })

        # Segundo registro com mesmo email
        response = client.post('/register', data={
            'name': 'User Two',
            'username': 'user2',
            'email': 'duplicate@example.com',
            'password': 'Pass456!',
            'confirm_password': 'Pass456!',
            'terms': 'on'
        }, follow_redirects=True)

        # Deve mostrar erro
        assert b'j\xc3\xa1 existe' in response.data or b'already' in response.data


class TestAPIEndpoints:
    """Testes de endpoints da API"""

    def test_process_receipt_without_auth(self, client):
        """Testa se API de processamento requer autenticação"""
        response = client.post('/api/process_receipt')
        assert response.status_code == 302 or response.status_code == 401

    def test_vehicle_fuel_count_without_auth(self, client):
        """Testa se API de contagem requer autenticação"""
        response = client.get('/api/vehicle/1/fuel_count')
        assert response.status_code == 302 or response.status_code == 401


class TestCacheHeaders:
    """Testes de headers de cache"""

    def test_cache_control_headers(self, client):
        """Verifica se headers de cache estão configurados"""
        response = client.get('/login')

        # Verificar se página tem meta tags de no-cache
        assert b'Cache-Control' in response.data or b'no-cache' in response.data


class TestSQLInjectionPrevention:
    """Testes de prevenção de SQL Injection"""

    def test_login_sql_injection_attempt(self, client):
        """Testa se login está protegido contra SQL injection"""
        malicious_input = "admin' OR '1'='1"

        response = client.post('/login', data={
            'email': malicious_input,
            'password': malicious_input
        }, follow_redirects=True)

        # Não deve permitir login
        assert response.status_code == 200
        assert b'Dashboard' not in response.data


class TestXSSPrevention:
    """Testes de prevenção de XSS"""

    def test_user_input_escaping(self, client):
        """Testa se inputs de usuário são escapados"""
        xss_payload = "<script>alert('XSS')</script>"

        response = client.post('/register', data={
            'name': xss_payload,
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'Pass123!',
            'confirm_password': 'Pass123!',
            'terms': 'on'
        }, follow_redirects=True)

        # Script não deve aparecer sem escape
        assert b"<script>alert('XSS')</script>" not in response.data


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
