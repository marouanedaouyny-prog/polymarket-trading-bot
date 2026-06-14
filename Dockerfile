FROM python:3.11-slim

RUN useradd -m -u 1000 user

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn==0.30.6 \
    python-dotenv==1.0.1 \
    slowapi==0.1.9 \
    requests==2.32.3 \
    pydantic==2.9.2 \
    aiohttp==3.10.0 \
    pandas==2.2.2 \
    numpy==1.26.4 \
    scikit-learn==1.5.1 \
    redis==5.1.1 \
    websockets==13.0 \
    sqlalchemy==2.0.35 \
    aiofiles==24.1.0

COPY --chown=user . .

USER user

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 7860

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]