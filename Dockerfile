FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

# Install dependencies first (cached as long as pyproject.toml/uv.lock don't change)
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-install-project

# Copy source and install the project
COPY . /app/
RUN uv sync --frozen

CMD python init_db.py && uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
