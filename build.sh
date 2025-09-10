#!/usr/bin/env bash
# Script de build para o Render

set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate