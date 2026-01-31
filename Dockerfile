FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for pdfplumber dependencies)
RUN apt-get update \
    && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Environment variables to ensure logs show up
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
