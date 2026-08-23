FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && apk add --no-cache libcap \
 && setcap cap_net_bind_service=+ep /usr/local/bin/python3.12
COPY app.py .
RUN adduser -D -u 10001 app
RUN chown -R app:app /app
USER app
EXPOSE 8000 53
CMD ["python", "app.py"]
