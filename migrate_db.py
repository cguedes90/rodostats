# Script para migrar banco de dados - tornar campos opcionais
from app import app, db
from sqlalchemy import text

def migrate_database():
    """Aplicar migrações necessárias"""
    with app.app_context():
        try:
            print("🔄 Iniciando migração do banco de dados...")
            
            # Tentar adicionar coluna color se não existir (PostgreSQL)
            try:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE vehicles ADD COLUMN color VARCHAR(30);'))
                    conn.commit()
                print("✅ Coluna 'color' adicionada com sucesso")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print("ℹ️ Coluna 'color' já existe")
                else:
                    print(f"⚠️ Aviso ao adicionar coluna color: {e}")
            
            # Tentar modificar license_plate para permitir NULL (PostgreSQL)
            try:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE vehicles ALTER COLUMN license_plate DROP NOT NULL;'))
                    conn.commit()
                print("✅ Campo 'license_plate' agora permite valores NULL")
            except Exception as e:
                if "does not exist" in str(e).lower():
                    print("ℹ️ Constraint NOT NULL em 'license_plate' já foi removida")
                else:
                    print(f"⚠️ Aviso ao modificar license_plate: {e}")
            
            # Verificar estrutura atual da tabela
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT column_name, is_nullable, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'vehicles' 
                    AND column_name IN ('license_plate', 'color')
                    ORDER BY column_name;
                """))
                
                print("\n📋 Estrutura atual da tabela vehicles:")
                for row in result:
                    nullable = "✅ NULL" if row[1] == 'YES' else "❌ NOT NULL"
                    print(f"  {row[0]}: {row[2]} - {nullable}")
            
            print("\n🎉 Migração concluída com sucesso!")
            return True
            
        except Exception as e:
            print(f"❌ Erro durante a migração: {e}")
            return False

if __name__ == '__main__':
    success = migrate_database()
    if success:
        print("\n✅ Banco de dados atualizado. Agora você pode cadastrar veículos sem placa e cor!")
    else:
        print("\n❌ Falha na migração. Verifique os erros acima.")
