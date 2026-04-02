# this dockerfile builds the backend api service
FROM mcr.microsoft.com/playwright/python:v1.53.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# browser deps and chromium are already available in playwright base image

COPY app ./app
COPY scripts ./scripts
COPY sql ./sql

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
