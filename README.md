# Money Control — Backend

## Local

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Render

- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`

Variáveis:

```
ENVIRONMENT=production
DATABASE_URL=<postgres do Render>
JWT_SECRET_KEY=<openssl rand -hex 32>
CORS_ORIGINS=https://seu-app.vercel.app
```
