FROM python:3.12-slim
ARG FLAG_2
RUN echo "$FLAG_2" > /flag.txt && chmod 644 /flag.txt
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 5000
CMD ["python", "app.py"]
