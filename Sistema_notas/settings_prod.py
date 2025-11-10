"""Django production settings for Sistema_notas project."""

from .settings import *
import os
from dotenv import load_dotenv
import dj_database_url

# Carrega variáveis de ambiente do arquivo .env se existir
env_file = os.path.join(BASE_DIR, '.env')
if os.path.isfile(env_file):
    load_dotenv(env_file)

# SECURITY WARNING: keep the secret key used in production secret!
# Em ambiente serverless, evitar crash se variável ausente, gerando chave efêmera.
import secrets
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    # Chave efêmera: válida apenas para o ciclo da função. Sessões podem se invalidar entre invocações.
    SECRET_KEY = secrets.token_urlsafe(64)
    import sys
    print('[startup-warning] SECRET_KEY não definido; usando chave efêmera para evitar 500.', file=sys.stderr)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Hosts permitidos em produção
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Configuração de banco de dados para produção
# Usa DATABASE_URL se disponível. Caso contrário, valida variáveis e aplica fallback seguro.
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(default=DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
    # Se variáveis essenciais estiverem ausentes em ambiente serverless, evitar conexões quebradas
    _required = ['DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT']
    _missing = [k for k in _required if not os.environ.get(k)]
    if _missing:
        import sys
        print(f"[startup-warning] Variáveis de banco ausentes ({', '.join(_missing)}); ativando backend dummy.", file=sys.stderr)
        DATABASES['default']['ENGINE'] = 'django.db.backends.dummy'

# Validação do driver de PostgreSQL para evitar falhas de import em ambiente serverless
_driver_ok = False
try:
    import psycopg  # psycopg 3
    _driver_ok = True
except Exception:
    try:
        import psycopg2  # psycopg2
        _driver_ok = True
    except Exception:
        _driver_ok = False

# Se o driver não estiver disponível e o ENGINE for PostgreSQL, evitar crash com backend dummy
if not _driver_ok:
    try:
        engine = DATABASES['default'].get('ENGINE')
    except Exception:
        engine = None
    if engine == 'django.db.backends.postgresql':
        import sys
        print('[startup-warning] PostgreSQL driver ausente; ativando backend dummy para evitar crash.', file=sys.stderr)
        DATABASES['default']['ENGINE'] = 'django.db.backends.dummy'

# Em ambientes sem banco (ENGINE dummy), evitar escrita de sessão no DB
try:
    _engine = DATABASES['default'].get('ENGINE')
except Exception:
    _engine = None
if _engine == 'django.db.backends.dummy':
    # Usa sessões baseadas em cookies assinados (sem persistência no banco)
    SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

# Em Vercel, preferir sessões por cookie para evitar acessos ao banco entre invocações
_is_vercel = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_ENV') is not None
if _is_vercel:
    SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

# Configurações de email para produção
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Configurações de arquivos estáticos
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Configurações de segurança adicionais
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True') == 'True'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Middleware adicional para produção
# Remove middlewares sensíveis a banco em ambientes serverless
_BASE_MIDDLEWARE = [mw for mw in MIDDLEWARE if mw != 'core.middleware.DatabaseQueryLogMiddleware']
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Para servir arquivos estáticos
] + _BASE_MIDDLEWARE

# Configuração do WhiteNoise para arquivos estáticos
Manifest_path = os.path.join(STATIC_ROOT, 'staticfiles.json')
if os.path.exists(Manifest_path):
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
else:
    # Fallback seguro quando o manifesto não foi gerado por collectstatic
    # Evita erro "Missing staticfiles manifest entry" e mantém compatibilidade
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Configuração de CORS
# Filtra valores vazios e espaços para evitar erros de configuração
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin and origin.strip()
]