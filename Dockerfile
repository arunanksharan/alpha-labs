FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main 2>/dev/null || \
    pip install --no-cache-dir \
      fastapi uvicorn[standard] polars pandas duckdb pyarrow yfinance \
      fredapi httpx numpy scipy statsmodels arch scikit-learn lightgbm xgboost \
      matplotlib plotly anthropic quantstats pyportfolioopt riskfolio-lib \
      lancedb langgraph litellm sqlalchemy alembic psycopg2-binary bcrypt \
      python-jose[cryptography] cryptography pydantic[email] python-dotenv slowapi

# Copy app
COPY . .

# Create data dirs
RUN mkdir -p data/store data/cache/research

# Expose
EXPOSE 8100

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8100/api/health || exit 1

# Run
CMD ["sh", "-c", "PYTHONPATH=. alembic upgrade head 2>/dev/null; PYTHONPATH=. python -c 'from db.seed import seed; seed()' 2>/dev/null; PYTHONPATH=. uvicorn api.server:app --host 0.0.0.0 --port 8100"]
