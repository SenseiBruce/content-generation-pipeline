FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-dev.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock \
    && pip install --no-cache-dir pytest==8.3.3 pytest-cov==5.0.0 pytest-socket==0.7.0 ruff==0.6.9

COPY . .

CMD ["pytest", "--cov=agents", "--cov=pipeline", "--cov-report=term", "--disable-socket"]
