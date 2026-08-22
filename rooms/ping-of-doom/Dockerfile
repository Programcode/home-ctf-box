FROM python:3.12-slim
ARG FLAG_3
RUN echo "$FLAG_3" > /flag.txt && chmod 644 /flag.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 5000
CMD ["python", "app.py"]
