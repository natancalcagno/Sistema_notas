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
- `Sistema_notas/wsgi.py`: adicionado fallback de inicialização com tratamento de erro. Se a app falhar ao iniciar, retorna 500 em JSON com dicas e log detalhado no stderr, evitando `FUNCTION_INVOCATION_FAILED` opaco.
- `Sistema_notas/settings_prod.py`: valida a presença do driver PostgreSQL (`psycopg` ou `psycopg2`). Se ausente e `ENGINE` for PostgreSQL, alterna para backend `dummy` para evitar crash em serverless, emitindo um aviso de startup.
- `vercel.json`: runtime atualizado para `python3.12` e rota principal corrigida para `"dest": "Sistema_notas/wsgi.py"`.

## Impacto
- O build do Vercel deixa de importar `sqlite3` durante `collectstatic`.
- O WSGI (`Sistema_notas/wsgi.py`) já expõe `app = application` e continua usando `settings_prod` em produção.

## Variáveis de ambiente necessárias no Vercel
- `DJANGO_SETTINGS_MODULE=Sistema_notas.settings_prod` (já setado pelo WSGI; o script de build também exporta).
- `SECRET_KEY` (obrigatória).
- `ALLOWED_HOSTS=.vercel.app,localhost` (ou configure internamente em `settings_prod`).
- `DATABASE_URL` (PostgreSQL recomendado; ex.: `postgres://user:pass@host:5432/db`).
- `DEBUG=false` em produção.
- Opcional: `VERCEL=1` é definido automaticamente pelo ambiente Vercel; usado para configurar logging console-only.

## Fluxo de build no Vercel
1. Instala dependências Python: `pip install -r requirements.txt`.
2. Exporta `DJANGO_SETTINGS_MODULE=Sistema_notas.settings_prod`.
3. Executa `python manage.py collectstatic --noinput --clear` (coleta estáticos em `staticfiles/`).
4. Publica os estáticos via `@vercel/static-build` (rotas direcionam `/static/(.*)` para os artefatos coletados).
5. Roda o WSGI via `@vercel/python` com entrypoint `Sistema_notas/wsgi.py` e variável `app`.

## Tratamento de erros e validações
- WSGI fallback: captura exceções na inicialização, imprime stacktrace nos logs da função e retorna uma resposta 500 informativa em JSON.
- Driver de Postgres: valida `psycopg`/`psycopg2` na importação. Se ausente, ativa backend `dummy` (apenas para evitar crash), com aviso nos logs. Em produção, forneça `DATABASE_URL` e garanta a instalação do driver para funcionamento pleno do banco.
- Logging serverless-safe: em Vercel, não escreve em disco; apenas console.

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

- Simular inicialização da função com fallback:
  ```
  $env:DJANGO_SETTINGS_MODULE="Sistema_notas.settings_prod"; $env:VERCEL="1"; python -c "import Sistema_notas.wsgi as w; print(type(w.app))"
  ```
  Se houver erro de inicialização, o fallback expõe `w.app` como função WSGI que retorna 500 com JSON.

## Referência rápida
- Arquivos alterados:
  - `build_files.sh`
  - `core/logging_config.py`
  - `Sistema_notas/settings.py`
- Sintoma original: `ModuleNotFoundError: No module named '_sqlite3'` durante `collectstatic` no Vercel.
- Solução: usar `settings_prod` no build e eliminar dependência circular em logging.

## Erros 500 pós-deploy e correção

### Sintomas observados
- Status 500 em `/`, `/favicon.ico` e `/favicon.png` nas funções do Vercel.
- Logs apontando falha no pipeline de resposta do runtime serverless.
- Build com aviso: `Skipping cache upload because no files were prepared`.

### Causa raiz
1) `CompressedManifestStaticFilesStorage` sem manifesto: ao renderizar templates com `{% static %}` ou ao servir assets, o storage exige `staticfiles.json`. Ausente, ocorre exceção e retorna 500.
2) `DatabaseQueryLogMiddleware` lendo `connection.queries` em ambiente sem banco configurado pode causar erros em serverless.

### Correções realizadas
- `Sistema_notas/settings_prod.py`:
  - Fallback automático para `CompressedStaticFilesStorage` quando `staticfiles.json` não existe.
  - Remoção de `core.middleware.DatabaseQueryLogMiddleware` do stack de produção para evitar dependência de banco.
- `vercel.json`: rotas unificadas para `Sistema_notas/wsgi.py` e estáticos servidos pelo WhiteNoise.

### Validação sugerida
1) Local (Windows PowerShell):
   - `setx DJANGO_SETTINGS_MODULE Sistema_notas.settings_prod` ou `$env:DJANGO_SETTINGS_MODULE="Sistema_notas.settings_prod"` temporário.
   - Garantir `DEBUG=false` e ausência de `staticfiles.json` para simular o fallback.
   - Acessar `/` e assets (`/favicon.ico`, `/static/...`) sem 500.
2) Produção (Vercel):
   - Verificar variáveis: `DJANGO_SETTINGS_MODULE`, `SECRET_KEY`, `ALLOWED_HOSTS`, `DEBUG=false`, `DATABASE_URL`.
   - Conferir Function Logs: ausência de exceções ao servir estáticos e na home.

### Observações
- Se desejar usar manifesto, execute `python manage.py collectstatic` e garanta que os artefatos estejam disponíveis no deploy.