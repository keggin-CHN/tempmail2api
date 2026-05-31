FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml .
COPY providers/ providers/
COPY server.py cli.py ./

RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

RUN useradd --create-home appuser
USER appuser

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8787/api/health')" || exit 1

CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8787"]
