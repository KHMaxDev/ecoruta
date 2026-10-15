# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Etapa 1: compilar el núcleo Rust (ecoruta_core) como wheel manylinux.
# Se usa la imagen oficial de maturin porque ya incluye Rust + toolchain,
# evitando dependencias de apt (bloqueado en el entorno de build).
# ---------------------------------------------------------------------------
FROM ghcr.io/pyo3/maturin:latest AS rust-builder

WORKDIR /io
COPY rust_core/ ./
RUN maturin build --release -i python3.12 --out /wheels

# ---------------------------------------------------------------------------
# Etapa 2: imagen de ejecución de la API FastAPI.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=rust-builder /wheels /wheels
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir /wheels/*.whl -r /tmp/requirements.txt \
    && rm -rf /wheels /tmp/requirements.txt

WORKDIR /app
COPY backend/ /app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
