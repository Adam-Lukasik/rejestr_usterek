FROM python:3.12-slim

WORKDIR /app

COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# Kod aplikacji NIE jest wbudowany w obraz - folder jest montowany (docker-compose.yml),
# dzieki czemu admin aktualizuje serwer z poziomu aplikacji (bez przebudowy obrazu).
ENV RU_DATA_DIR=/app/data \
    RU_STATIC_DIR=/app \
    PYTHONUNBUFFERED=1

EXPOSE 5050

CMD ["python", "server_main.py"]
