# ---- 1. Base image ----
FROM python:3.11-slim

# ---- 2. Install Poetry ----
RUN sudo apt install poetry

# ---- 3. Set working directory ----
WORKDIR /app

# ---- 4. Copy dependency files first ----
COPY pyproject.toml poetry.lock ./

# ---- 5. Install dependencies (no dev dependencies, no interactive prompts) ----
RUN poetry install --no-root --no-dev

# ---- 6. Copy the rest of your app ----
COPY . .

# ---- 7. Run your app ----
CMD ["poetry", "run", "python", "app/main.py"]
