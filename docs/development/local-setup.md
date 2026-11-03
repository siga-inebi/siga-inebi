# Local Setup

## Lineamientos ya decididos

- Frontend: React + Vite + JavaScript.
- Backend: Django + DRF.
- Base local inicial: SQLite.
- Base para pruebas: PostgreSQL.
- Docker recomendado para stack completo.

## Backend local con PostgreSQL en Docker

### Linux/macOS

```bash
cp .env.example .env
docker compose up -d db
cd backend
/usr/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
DATABASE_ENGINE=postgresql \
DATABASE_NAME=siga_inebi \
DATABASE_USER=siga_inebi \
DATABASE_PASSWORD=siga_inebi_dev_password \
DATABASE_HOST=127.0.0.1 \
DATABASE_PORT=5432 \
python manage.py migrate
DATABASE_ENGINE=postgresql \
DATABASE_NAME=siga_inebi \
DATABASE_USER=siga_inebi \
DATABASE_PASSWORD=siga_inebi_dev_password \
DATABASE_HOST=127.0.0.1 \
DATABASE_PORT=5432 \
python manage.py runserver 127.0.0.1:8001
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
docker compose up -d db
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements/dev.txt
$env:DATABASE_ENGINE = "postgresql"
$env:DATABASE_NAME = "siga_inebi"
$env:DATABASE_USER = "siga_inebi"
$env:DATABASE_PASSWORD = "siga_inebi_dev_password"
$env:DATABASE_HOST = "127.0.0.1"
$env:DATABASE_PORT = "5432"
python manage.py migrate
python manage.py runserver 127.0.0.1:8001
```

## Backend local con SQLite

SQLite es solo para desarrollo rapido. No usar para pruebas automatizadas, staging ni produccion.

```bash
cd backend
source .venv/bin/activate
DATABASE_ENGINE=sqlite python manage.py migrate
DATABASE_ENGINE=sqlite python manage.py runserver 127.0.0.1:8002
```

## Frontend local

```bash
cd frontend
npm ci
VITE_API_URL=http://127.0.0.1:8001/api/v1 npm run dev -- --host 127.0.0.1 --port 4173
```

## URLs y diferencias

- URL usada por navegador con Docker: `http://127.0.0.1:8000/api/v1`
- Host interno Docker entre contenedores: `http://backend:8000/api/v1`
- URL usada por frontend local sin Docker para backend local: `http://127.0.0.1:8001/api/v1`

## Observacion de Python

En este entorno se verifico que `/usr/local/bin/python3` carece de modulo `_ssl`. Se uso `/usr/bin/python3` para crear `backend/.venv`. Si tu `python3` ya incluye SSL, puedes usarlo normalmente.

- Confirmar herramientas base del equipo.
- Definir version minima de Python y Node.
- Definir comandos oficiales.
