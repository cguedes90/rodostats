@echo off
REM ========================================
REM SCRIPT DE CORREÇÕES AUTOMÁTICAS
REM RodoStats - Preparação para Apps Mobile
REM ========================================

echo ========================================
echo RODOSTATS - APLICANDO CORRECOES
echo ========================================
echo.

REM Verificar se está na pasta correta
if not exist "app.py" (
    echo [ERRO] app.py nao encontrado!
    echo Por favor, execute este script na raiz do projeto RodoStats
    pause
    exit /b 1
)

echo [OK] Projeto RodoStats encontrado!
echo.

REM ========================================
REM 1. BACKUP AUTOMÁTICO
REM ========================================
echo Criando backup antes das alteracoes...
set BACKUP_DIR=backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%
set BACKUP_DIR=%BACKUP_DIR: =0%
mkdir "%BACKUP_DIR%" 2>nul

REM Fazer backup
copy app.py "%BACKUP_DIR%\" >nul 2>&1
copy templates\index.html "%BACKUP_DIR%\" >nul 2>&1
copy templates\base.html "%BACKUP_DIR%\" >nul 2>&1
copy static\manifest.json "%BACKUP_DIR%\" >nul 2>&1

echo [OK] Backup criado em: %BACKUP_DIR%
echo.

REM ========================================
REM 2. CONFIGURAR .ENV
REM ========================================
echo Configurando arquivo .env...

if exist ".env" (
    echo [AVISO] Arquivo .env ja existe!
    set /p OVERWRITE="Deseja sobrescrever? (S/N): "
    if /i "%OVERWRITE%"=="S" goto CREATE_ENV
    echo Mantendo .env atual...
    goto SKIP_ENV
)

:CREATE_ENV
(
echo # ========================================
echo # RODO STATS - Configuracoes de Ambiente
echo # ========================================
echo.
echo # SEGURANCA
echo SESSION_SECRET=rodostats-super-secret-key-2024-change-this-in-production
echo.
echo # BANCO DE DADOS
echo DATABASE_URL=postgresql://neondb_owner:npg_ArdO9L4sGxUD@ep-sweet-shape-ac6v4rp3-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require^&channel_binding=require
echo.
echo # INTELIGENCIA ARTIFICIAL
echo GROQ_API_KEY=gsk_demo_key
echo.
echo # EMAIL - GMAIL
echo MAIL_SERVER=smtp.gmail.com
echo MAIL_PORT=587
echo MAIL_USE_TLS=true
echo MAIL_USERNAME=cedriquepereira@gmail.com
echo MAIL_PASSWORD=icrxqxvchppkgylq
echo MAIL_DEFAULT_SENDER=cedriquepereira@gmail.com
echo.
echo # PRODUCAO
echo PORT=5000
echo FLASK_ENV=production
echo APP_URL=https://rodostats.vercel.app
) > .env

echo [OK] Arquivo .env configurado!

:SKIP_ENV
echo.

REM ========================================
REM 3. LIMPAR ARQUIVOS DESNECESSÁRIOS
REM ========================================
echo Removendo arquivos desnecessarios...

if exist "app_backup.py" (
    move app_backup.py "%BACKUP_DIR%\" >nul 2>&1
    echo [OK] Removido: app_backup.py
)

if exist "app_new.py" (
    move app_new.py "%BACKUP_DIR%\" >nul 2>&1
    echo [OK] Removido: app_new.py
)

if exist "tesseract_config.py" (
    move tesseract_config.py "%BACKUP_DIR%\" >nul 2>&1
    echo [OK] Removido: tesseract_config.py
)

echo.

REM ========================================
REM 4. CRIAR SCRIPT DE TESTE
REM ========================================
echo Criando script de teste de email...

(
echo #!/usr/bin/env python3
echo # -*- coding: utf-8 -*-
echo """Teste rapido de email do RodoStats"""
echo.
echo import os
echo from dotenv import load_dotenv
echo.
echo load_dotenv(^)
echo.
echo print("="*60^)
echo print("TESTE DE EMAIL - RODO STATS"^)
echo print("="*60^)
echo print(^)
echo.
echo try:
echo     from flask import Flask
echo     from flask_mail import Mail, Message
echo.    
echo     app = Flask(__name__^)
echo     app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER'^)
echo     app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587^)^)
echo     app.config['MAIL_USE_TLS'] = True
echo     app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME'^)
echo     app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD'^)
echo     app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER'^)
echo.    
echo     mail = Mail(app^)
echo.    
echo     dest_email = input("Digite o email de destino: "^).strip(^)
echo.    
echo     with app.app_context(^):
echo         msg = Message(
echo             subject="Teste RodoStats",
echo             recipients=[dest_email],
echo             html="^<h1^>Email funcionando!^</h1^>^<p^>RodoStats pronto!^</p^>"
echo         ^)
echo.        
echo         print("Enviando..."^)
echo         mail.send(msg^)
echo         print("EMAIL ENVIADO COM SUCESSO!"^)
echo.        
echo except Exception as e:
echo     print(f"ERRO: {e}"^)
) > test_email.py

echo [OK] test_email.py criado
echo.

REM ========================================
REM ATUALIZAR MANIFEST
REM ========================================
echo Atualizando manifest.json...

(
echo {
echo   "name": "Rodo Stats - Controle de Combustivel",
echo   "short_name": "RodoStats",
echo   "description": "Controle inteligente de combustivel com IA",
echo   "start_url": "/",
echo   "display": "standalone",
echo   "background_color": "#1a1a1a",
echo   "theme_color": "#4A90E2",
echo   "orientation": "portrait",
echo   "categories": ["finance", "productivity"],
echo   "icons": [
echo     {
echo       "src": "/static/icons/icon-192.png",
echo       "sizes": "192x192",
echo       "type": "image/png",
echo       "purpose": "any maskable"
echo     },
echo     {
echo       "src": "/static/icons/icon-512.png",
echo       "sizes": "512x512",
echo       "type": "image/png",
echo       "purpose": "any maskable"
echo     }
echo   ]
echo }
) > static\manifest.json

echo [OK] manifest.json atualizado
echo.

REM ========================================
REM RESUMO FINAL
REM ========================================
echo.
echo ========================================
echo CORRECOES APLICADAS COM SUCESSO!
echo ========================================
echo.
echo O que foi feito:
echo   [OK] Backup criado em: %BACKUP_DIR%
echo   [OK] Arquivo .env configurado
echo   [OK] Arquivos desnecessarios removidos
echo   [OK] Script de teste criado
echo   [OK] manifest.json atualizado
echo.
echo TESTE O EMAIL AGORA:
echo   python test_email.py
echo.
echo PROXIMO PASSO:
echo   git add .
echo   git commit -m "Correcoes pre-lancamento"
echo   git push
echo.
echo DICA: Se der erro, restaure do backup:
echo   copy %BACKUP_DIR%\* .
echo.
pause
