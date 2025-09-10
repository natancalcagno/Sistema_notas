import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Sistema_notas.settings")
django.setup()

from core.models import Usuario

# Criar usuário administrador
try:
    if not Usuario.objects.filter(username='natan').exists():
        usuario = Usuario.objects.create_user(
            username='natan',
            password='natan123',  # Você deve alterar esta senha depois
            first_name='Natan',
            email='natan@example.com',
            tipo_usuario='admin',
            is_staff=True,
            is_superuser=True
        )
        print("Usuário natan criado com sucesso como administrador!")
        print("Username: natan")
        print("Senha: natan123")
        print("IMPORTANTE: Por favor, altere a senha após o primeiro login!")
    else:
        usuario = Usuario.objects.get(username='natan')
        usuario.tipo_usuario = 'admin'
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.save()
        print("Usuário natan atualizado como administrador!")
except Exception as e:
    print(f"Erro ao criar/atualizar usuário: {str(e)}")