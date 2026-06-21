FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    g++ \
    && rm -rf /var/lib/apt-lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt \
    && rm -rf /root/.cache/pip

COPY . .

RUN mkdir -p output

CMD ["python", "__main__.py"]
