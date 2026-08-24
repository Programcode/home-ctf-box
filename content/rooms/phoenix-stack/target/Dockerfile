FROM python:3.12-alpine
WORKDIR /app
COPY app.py .
RUN adduser -D -u 10001 app
RUN chown -R app:app /app
USER app
EXPOSE 4000
CMD ["python", "app.py"]
