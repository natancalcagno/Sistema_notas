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
import json
import traceback

# Adiciona o diretório do projeto ao path
path = str(Path(__file__).resolve().parent.parent)
if path not in sys.path:
    sys.path.append(path)

# Define o módulo de configurações com base no ambiente
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Sistema_notas.settings_prod')

# Inicializa a aplicação WSGI com tratamento robusto de erros.
# Em ambientes serverless (Vercel), um crash silencioso derruba a função.
# Com este fallback, retornamos 500 com detalhes úteis e evitamos falhas opacas.
try:
    application = get_wsgi_application()
    app = application  # Expor a variável pública `app` para o runtime do Vercel
except Exception as exc:
    # Log detalhado no stderr para aparecer nos logs da função
    traceback.print_exc()

    def app(environ, start_response):
        start_response(
            '500 Internal Server Error',
            [('Content-Type', 'application/json; charset=utf-8')]
        )
        payload = {
            'error': 'WSGI initialization failed',
            'message': str(exc),
            'hint': 'Check SECRET_KEY, DATABASE_URL/driver, and logging configuration.',
            'env': {
                'DJANGO_SETTINGS_MODULE': os.environ.get('DJANGO_SETTINGS_MODULE'),
                'VERCEL': os.environ.get('VERCEL'),
            }
        }
        return [json.dumps(payload, ensure_ascii=False).encode('utf-8')]
