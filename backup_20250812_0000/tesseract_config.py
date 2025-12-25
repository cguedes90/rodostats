# Configuração do Tesseract OCR
import os
import pytesseract

def configure_tesseract():
    """Configura o Tesseract OCR para Windows"""
    # Windows
    if os.name == 'nt':
        # Caminhos comuns do Tesseract no Windows
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Users\usuario\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"Tesseract configurado em: {path}")
                return True
        
        # Se não encontrar, usar variável de ambiente
        tesseract_cmd = os.environ.get('TESSERACT_CMD')
        if tesseract_cmd and os.path.exists(tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            print(f"Tesseract configurado via variável de ambiente: {tesseract_cmd}")
            return True
        
        print("Tesseract OCR não encontrado. Instale ou configure TESSERACT_CMD")
        return False
    
    return True  # Linux/Mac geralmente têm no PATH
