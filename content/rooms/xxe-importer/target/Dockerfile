FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN adduser -D -u 10001 app && touch /flag.txt && chown app:app /flag.txt
RUN chown -R app:app /app
USER app
EXPOSE 8000
CMD ["python", "app.py"]
