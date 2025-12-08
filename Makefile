# --- VARIABLES ---
BACKEND_DIR = backend
FRONTEND_DIR = frontend

# --- COMMANDS ---
.PHONY: install-backend install-frontend run-backend run-frontend run-all lint format test clean

# --- SETUP ---
install-backend:
	cd $(BACKEND_DIR) && poetry install

install-frontend:
	cd $(FRONTEND_DIR) && npm install

install: install-backend install-frontend

# --- RUN ---
run-backend: install-backend
	cd $(BACKEND_DIR) && poetry run python src/main.py

run-frontend:install-frontend
	cd $(FRONTEND_DIR) && npm run dev