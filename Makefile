.PHONY: setup install-backend install-frontend db-init db-seed train-all build-rag run-backend run-frontend run-all test clean

setup: install-backend install-frontend db-init

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

db-init:
	cd backend && alembic upgrade head

db-seed:
	python scripts/seed_database.py

train-all:
	python scripts/train_all.py

build-rag:
	cd rag && python build_index.py

run-backend:
	cd backend && uvicorn main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev

run-all:
	make run-backend & make run-frontend

test:
	cd backend && pytest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf node_modules
	rm -rf .next
