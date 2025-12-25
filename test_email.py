#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teste rapido de email do RodoStats"""

import os
from dotenv import load_dotenv

load_dotenv()

print("="*60)
print("TESTE DE EMAIL - RODO STATS")
print("="*60)
print()

try:
    from flask import Flask
    from flask_mail import Mail, Message
    
    app = Flask(__name__)
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    
    mail = Mail(app)
    
    dest_email = input("Digite o email de destino: ").strip()
    
    with app.app_context():
        msg = Message(
            subject="Teste RodoStats",
            recipients=[dest_email],
            html="^<h1^>Email funcionando!^</h1^>^<p^>RodoStats pronto!^</p^>"
        )
        
        print("Enviando...")
        mail.send(msg)
        print("EMAIL ENVIADO COM SUCESSO!")
        
except Exception as e:
    print(f"ERRO: {e}")
