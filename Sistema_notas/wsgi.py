"""
WSGI config for Sistema_notas project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

# Adiciona o diretório do projeto ao path
path = str(Path(__file__).resolve().parent.parent)
if path not in sys.path:
    sys.path.append(path)

# Define o módulo de configurações com base no ambiente
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Sistema_notas.settings_prod')

application = get_wsgi_application()
