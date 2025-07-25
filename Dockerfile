
FROM python:3.11-slim

ENV PLAYWRIGHT_BROWSERS_PATH=0

RUN apt-get update && apt-get install -y wget gnupg libglib2.0-0 libnss3 libgconf-2-4 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libasound2 libxshmfence1 libx11-xcb1 xvfb fonts-liberation libappindicator3-1 lsb-release \
    ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    python -m playwright install --with-deps chromium

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
