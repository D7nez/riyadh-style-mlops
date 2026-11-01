# syntax=docker/dockerfile:1
FROM python:3.12-slim
WORKDIR /app
ENV PROJECT_ROOT=/app PYTHONUNBUFFERED=1 HF_HOME=/home/app/.cache/huggingface
COPY requirements-tested.txt ./
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements-tested.txt
ARG INSTALL_SEMANTIC=false
RUN --mount=type=cache,target=/root/.cache/pip if [ "$INSTALL_SEMANTIC" = "true" ]; then pip install 'sentence-transformers>=3,<6'; fi
RUN useradd -m -u 10001 app && mkdir -p /home/app/.cache/huggingface /app/.cache /app/reports /app/mlflow && chown -R app:app /app /home/app
COPY --chown=app:app . .
RUN pip install --no-deps --no-build-isolation -e .
USER app
EXPOSE 8000
CMD ["uvicorn","styleops.api:app","--host","0.0.0.0","--port","8000"]
