FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN addgroup --system --gid 10001 nimbusx \
    && adduser --system --uid 10001 --ingroup nimbusx --home /app nimbusx

COPY backend/requirements.runtime.lock /tmp/requirements.runtime.lock
RUN python -m pip install --require-hashes -r /tmp/requirements.runtime.lock

COPY backend/nimbusx/ /app/nimbusx/

USER nimbusx
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "nimbusx.main:app", "--host", "0.0.0.0", "--port", "8000"]