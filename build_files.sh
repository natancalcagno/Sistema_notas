#!/usr/bin/env bash
set -euo pipefail

# Instala dependências e coleta estáticos para servir via Vercel static build
pip install -r requirements.txt
python manage.py collectstatic --noinput --clear