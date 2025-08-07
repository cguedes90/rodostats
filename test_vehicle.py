# Teste de cadastro de veículo sem placa e cor
from app import app, db, User, Vehicle

def test_vehicle_creation():
    """Testar criação de veículo sem placa e cor"""
    with app.app_context():
        try:
            print("🧪 Testando cadastro de veículo sem placa e cor...")
            
            # Buscar um usuário existente ou criar um de teste
            user = User.query.first()
            if not user:
                print("❌ Nenhum usuário encontrado. Crie uma conta primeiro.")
                return False
            
            # Criar veículo de teste sem placa e cor
            test_vehicle = Vehicle(
                user_id=user.id,
                name="Carro Teste",
                brand="Toyota",
                model="Corolla",
                year=2020,
                license_plate=None,  # Sem placa
                color=None,  # Sem cor
                fuel_type="gasoline",
                tank_capacity=45.0
            )
            
            db.session.add(test_vehicle)
            db.session.commit()
            
            print("✅ Veículo criado com sucesso!")
            print(f"   ID: {test_vehicle.id}")
            print(f"   Nome: {test_vehicle.name}")
            print(f"   Marca: {test_vehicle.brand}")
            print(f"   Modelo: {test_vehicle.model}")
            print(f"   Placa: {test_vehicle.license_plate or 'Não informada'}")
            print(f"   Cor: {test_vehicle.color or 'Não informada'}")
            
            # Remover veículo de teste
            db.session.delete(test_vehicle)
            db.session.commit()
            print("🗑️ Veículo de teste removido")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro no teste: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = test_vehicle_creation()
    if success:
        print("\n🎉 Teste concluído com sucesso! O cadastro de veículos sem placa e cor está funcionando!")
    else:
        print("\n❌ Teste falhou. Verifique os erros acima.")
