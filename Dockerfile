FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV IDC_SERVER_HOST=0.0.0.0
ENV IDC_SERVER_PORT=8080
ENV IDC_SERVER_USE_WAITRESS=1
ENV IDC_TESSERACT_CMD=/usr/bin/tesseract
ENV IDC_OCR_LANG=eng

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-chi-sim \
        tesseract-ocr-chi-tra \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements_server.txt ./
RUN pip install --no-cache-dir -r requirements_server.txt

COPY . .

RUN mkdir -p /data/uploads /data/reports

ENV IDC_SERVER_UPLOAD_DIR=/data/uploads
ENV IDC_SERVER_REPORT_DIR=/data/reports

EXPOSE 8080

CMD ["python", "server/idc_server.py"]
