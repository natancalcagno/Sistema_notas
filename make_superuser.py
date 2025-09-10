import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Sistema_notas.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

try:
    user = User.objects.get(username='natan')
    if not user.is_superuser:
        user.is_superuser = True
        user.is_staff = True
        user.save()
        print("Usuário 'natan' foi transformado em superusuário com sucesso!")
    else:
        print("O usuário 'natan' já é um superusuário.")
except User.DoesNotExist:
    print("O usuário 'natan' não foi encontrado no sistema.")