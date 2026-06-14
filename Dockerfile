FROM python:3.11-slim
RUN useradd -m -u 1000 user
WORKDIR /app
COPY --chown=user server.py /app/server.py
USER user
EXPOSE 7860
CMD ["python", "/app/server.py"]