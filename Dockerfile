FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn python-dotenv slowapi requests pydantic aiohttp pandas numpy redis websockets sqlalchemy aiofiles
RUN pip install --no-cache-dir --only-binary :all: scikit-learn

COPY . .

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 7860

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]