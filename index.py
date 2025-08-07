# Arquivo específico para Vercel
from app import app

# Vercel precisa de uma função chamada 'app' ou 'handler'
if __name__ == "__main__":
    app.run()
