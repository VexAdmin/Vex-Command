.PHONY: dev api web install test test-sql db-up db-sync-raptor api-sql

install:
	python3.12 -m venv .venv
	.venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm install

db-up:
	docker compose up -d postgres

# Copy orgs/users/scans from local vex-raptor-postgres → Command PG :5433
db-sync-raptor:
	bash scripts/sync-raptor-local.sh

# API with SQL + real Raptor tables (after db-sync-raptor). Auth stays mock in dev.
api-sql:
	DATA_SOURCE=sql FOUNDER_DEV_STUB=false \
	DATABASE_URL=postgresql://vex_founder:vex_founder_dev@127.0.0.1:5433/vex_founder \
	RAPTOR_HEALTH_URL=http://127.0.0.1:8000/health \
	$(MAKE) api

api:
	.venv/bin/uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8081

web:
	cd frontend && npm run dev

dev:
	@echo "Terminal A: make db-up && make api"
	@echo "Terminal B: make web"
	@echo "SQL mode: export DATABASE_URL=postgresql://vex_founder:vex_founder_dev@127.0.0.1:5433/vex_founder"

test:
	.venv/bin/python -m pytest backend/tests/test_api.py backend/tests/test_kpis.py backend/tests/test_auth.py backend/tests/test_pipeline.py -q

test-sql: db-up
	.venv/bin/python -m pytest backend/tests/test_f1_sql.py backend/tests/test_f1_pipeline.py -q

test-all: db-up
	.venv/bin/python -m pytest backend/tests -q
	cd frontend && npm test
