FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PORT=10000
ENV HOST=0.0.0.0
ENV TZ=Asia/Tashkent

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libgomp1 \
    tzdata \
    curl \
    && ln -snf /usr/share/zoneinfo/Asia/Tashkent /etc/localtime \
    && echo "Asia/Tashkent" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Compile GodMode v50 C-Native Engine with OpenMP
RUN gcc -O3 -fopenmp -shared -fPIC godmode_engine.c -o libgodmode_engine.so || true

RUN chmod +x start.sh

EXPOSE 10000

CMD ["bash", "start.sh"]
