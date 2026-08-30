FROM python:3.12-slim

# faster-whisper audioni `av` orqali dekodlaydi, ffmpeg esa zaxira variant
# (Telegram'ning .oga/opus va video_note mp4 fayllari uchun).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=2

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Whisper modelini image ichiga oldindan yuklaymiz: cold start tez bo'ladi
# va model uchun volume joyi band qilinmaydi.
ARG WHISPER_MODEL=base
RUN python -c "from huggingface_hub import snapshot_download; \
    snapshot_download('Systran/faster-whisper-${WHISPER_MODEL}')"

COPY . .

CMD ["python", "bot.py"]
