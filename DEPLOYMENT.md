# Deploy no Vercel — Sistema_notas

Este documento registra a causa raiz do erro no build, as correções aplicadas e como testar/operar o deploy no Vercel.

## Causa raiz
- O build no Vercel executava `./build_files.sh` para coletar estáticos.
- O script rodava `python manage.py collectstatic` com o `DJANGO_SETTINGS_MODULE` padrão (`Sistema_notas.settings`).
- `settings.py` usa `sqlite3` por padrão; no ambiente do Vercel não existe o módulo nativo `_sqlite3`, causando `ModuleNotFoundError: No module named '_sqlite3'` e falha do build.

## Correções aplicadas
- `build_files.sh`: exporta `DJANGO_SETTINGS_MODULE=Sistema_notas.settings_prod` antes de rodar `collectstatic`, evitando carregar o backend `sqlite3`.
- `core/logging_config.py`: alterado `setup_logging(base_dir=None)` para aceitar `base_dir` como parâmetro e não depender do `django.conf.settings` durante o carregamento dos settings (evita erro de import circular). Há um fallback seguro para resolver `BASE_DIR` quando não fornecido.
- `Sistema_notas/settings.py`: passa `BASE_DIR` explicitamente para `setup_logging`, via `LOGGING = setup_logging(base_dir=str(BASE_DIR))`.

## Impacto
- O build do Vercel deixa de importar `sqlite3` durante `collectstatic`.
- O WSGI (`Sistema_notas/wsgi.py`) já expõe `app = application` e continua usando `settings_prod` em produção.

## Variáveis de ambiente necessárias no Vercel
- `DJANGO_SETTINGS_MODULE=Sistema_notas.settings_prod` (já setado pelo WSGI; o script de build também exporta).
- `SECRET_KEY` (obrigatória).
- `ALLOWED_HOSTS=.vercel.app,localhost` (ou configure internamente em `settings_prod`).
- `DATABASE_URL` (PostgreSQL recomendado; ex.: `postgres://user:pass@host:5432/db`).
- `DEBUG=false` em produção.

## Fluxo de build no Vercel
1. Instala dependências Python: `pip install -r requirements.txt`.
2. Exporta `DJANGO_SETTINGS_MODULE=Sistema_notas.settings_prod`.
3. Executa `python manage.py collectstatic --noinput --clear` (coleta estáticos em `staticfiles/`).
4. Publica os estáticos via `@vercel/static-build` (rotas direcionam `/static/(.*)` para os artefatos coletados).
5. Roda o WSGI via `@vercel/python` com entrypoint `Sistema_notas/wsgi.py` e variável `app`.

## Testes locais
- Coleta de estáticos padrão (sqlite local):
  ```
  python manage.py collectstatic --noinput --clear
  ```
- Coleta de estáticos simulando produção:
  ```
  # Windows PowerShell
  $env:DJANGO_SETTINGS_MODULE="Sistema_notas.settings_prod"; python manage.py collectstatic --noinput --clear
  ```
  Observação: em ambientes sem `psycopg2-binary` para a versão de Python local, pode haver erro de import do driver do PostgreSQL. No Vercel (Python 3.12) o pacote precompilado é suportado.

## Referência rápida
- Arquivos alterados:
  - `build_files.sh`
  - `core/logging_config.py`
  - `Sistema_notas/settings.py`
- Sintoma original: `ModuleNotFoundError: No module named '_sqlite3'` durante `collectstatic` no Vercel.
- Solução: usar `settings_prod` no build e eliminar dependência circular em logging.