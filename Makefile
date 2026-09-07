.PHONY: dev api web install test test-sql db-up

install:
	python3.12 -m venv .venv
	.venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm install

db-up:
	docker compose up -d postgres

api:
	.venv/bin/uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8081

web:
	cd frontend && npm run dev

dev:
	@echo "Terminal A: make db-up && make api"
	@echo "Terminal B: make web"
	@echo "SQL mode: export DATABASE_URL=postgresql://vex_founder:vex_founder_dev@127.0.0.1:5433/vex_founder"

test:
	.venv/bin/python -m pytest backend/tests/test_api.py backend/tests/test_kpis.py backend/tests/test_auth.py -q

test-sql: db-up
	.venv/bin/python -m pytest backend/tests/test_f1_sql.py -q

test-all: db-up
	.venv/bin/python -m pytest backend/tests -q
	cd frontend && npm test
