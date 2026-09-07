FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY sql ./sql
ENV SQL_DIR=/app/sql
ENV API_HOST=0.0.0.0 API_PORT=8081
EXPOSE 8081
CMD ["sh", "-c", "uvicorn app.main:app --host ${API_HOST} --port ${API_PORT}"]
