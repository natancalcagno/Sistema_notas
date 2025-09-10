import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Sistema_notas.settings")
django.setup()

from core.models import Usuario

try:
    usuario = Usuario.objects.get(username='natan')
    print(f"Status atual do usuário natan:")
    print(f"- É superusuário: {usuario.is_superuser}")
    print(f"- É staff: {usuario.is_staff}")
    print(f"- Tipo de usuário: {usuario.tipo_usuario}")
    
    # Garantir que o usuário seja admin
    if usuario.tipo_usuario != 'admin':
        usuario.tipo_usuario = 'admin'
        usuario.is_staff = True
        usuario.save()
        print("\nUsuário atualizado:")
        print(f"- Tipo de usuário alterado para: {usuario.tipo_usuario}")
        print(f"- Is staff alterado para: {usuario.is_staff}")
    else:
        print("\nO usuário já está configurado como administrador.")
        
except Usuario.DoesNotExist:
    print("Usuário natan não encontrado no sistema.")