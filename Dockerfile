FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=10001:10001 app.py .
COPY --chown=10001:10001 static/ ./static/
USER 10001:10001
ENV PYTHONUNBUFFERED=1 PORT=8000
EXPOSE 8000
CMD ["python", "app.py", "--host", "0.0.0.0"]
