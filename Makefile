.PHONY: dev dev-api dev-web types-api install-api

# Arranque conjunto API + Vite (requiere: npm install en la raíz, pip -r apps/api/requirements.txt)
dev:
	npm run dev

dev-api:
	PYTHONPATH=$(CURDIR) python3 -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload

dev-web:
	cd apps/web && npm run dev

install-api:
	python3 -m pip install -r apps/api/requirements.txt

# Regenerar OpenAPI JSON y tipos TS del front
types-api:
	PYTHONPATH=$(CURDIR) python3 scripts/export_openapi.py > apps/web/openapi.json
	cd apps/web && npm run types:api
