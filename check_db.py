import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Sistema_notas.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.db import connection

Usuario = get_user_model()

def check_database():
    print("Verificando banco de dados...")
    with connection.cursor() as cursor:
        # Verifica se a tabela de usuários existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='core_usuario';
        """)
        if not cursor.fetchone():
            print("Tabela de usuários não encontrada!")
            return False
        
        # Verifica se há usuários cadastrados
        cursor.execute("SELECT COUNT(*) FROM core_usuario;")
        count = cursor.fetchone()[0]
        print(f"Total de usuários cadastrados: {count}")
        return True

def create_admin_user():
    try:
        # Tenta criar o usuário
        usuario = Usuario.objects.create_user(
            username='natan',
            email='natan@example.com',
            password='natan123',
            first_name='Natan',
            tipo_usuario='admin',
            is_staff=True,
            is_superuser=True
        )
        print("\nUsuário admin criado com sucesso!")
        print("Username: natan")
        print("Senha: natan123")
        return True
    except Exception as e:
        print(f"\nErro ao criar usuário: {str(e)}")
        return False

def list_users():
    print("\nListando todos os usuários:")
    print("-" * 50)
    for user in Usuario.objects.all():
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Tipo: {user.tipo_usuario}")
        print(f"É staff: {user.is_staff}")
        print(f"É superuser: {user.is_superuser}")
        print("-" * 50)

if __name__ == "__main__":
    if check_database():
        # Lista usuários atuais
        list_users()
        
        # Verifica se o usuário natan existe
        if not Usuario.objects.filter(username='natan').exists():
            print("\nUsuário 'natan' não encontrado. Criando...")
            create_admin_user()
        else:
            usuario = Usuario.objects.get(username='natan')
            print("\nUsuário 'natan' encontrado. Atualizando permissões...")
            usuario.tipo_usuario = 'admin'
            usuario.is_staff = True
            usuario.is_superuser = True
            usuario.save()
            print("Permissões atualizadas!")
            
        # Lista usuários após as alterações
        print("\nUsuários após alterações:")
        list_users()
    else:
        print("Problemas com o banco de dados! Verifique as migrações.")