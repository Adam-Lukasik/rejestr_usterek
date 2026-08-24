FROM python:3.11-slim

# Ustawienie strefy czasowej i kodowania UTF-8
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Warsaw

WORKDIR /app

# Instalacja zależności systemowych dla obsługi bibliotek multimedialnych
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Skopiowanie plików aplikacji
COPY . .

# Port serwera REST API
EXPOSE 5050

# Start serwera produkcyjnego WSGI (waitress)
CMD ["python", "-c", "import app; app.init_db(); from waitress import serve; print('Serwer Rejestr Usterek uruchomiony na porcie 5050'); serve(app.app, host='0.0.0.0', port=5050, threads=8)"]
