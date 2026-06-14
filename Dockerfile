FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir --only-binary :all: \
    fastapi>=0.104.0 \
    uvicorn>=0.24.0 \
    requests>=2.31.0 \
    pandas>=2.1.0 \
    numpy>=1.26.0 \
    scikit-learn>=1.3.0 \
    python-dotenv>=1.0.0 \
    slowapi>=0.1.9 \
    aiohttp>=3.8.0 \
    redis>=4.5.0

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 7860

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "7860"]