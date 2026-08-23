FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN adduser -D -u 10001 app
RUN chown -R app:app /app
USER app
EXPOSE 8000 7000/udp 9000/udp 9999/udp
CMD ["python", "app.py"]
