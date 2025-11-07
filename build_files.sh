#!/usr/bin/env bash
set -euo pipefail

# Instala dependências e coleta estáticos para servir via Vercel static build
pip install -r requirements.txt

# Use configurações de produção para evitar dependência do sqlite3 no ambiente do Vercel
export DJANGO_SETTINGS_MODULE=Sistema_notas.settings_prod

# Coleta arquivos estáticos
python manage.py collectstatic --noinput --clear