FROM python:3.12-slim AS base

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
RUN pip install --upgrade pip && pip install -e .

COPY backend backend
COPY scripts scripts
COPY sim sim

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
