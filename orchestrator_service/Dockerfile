FROM python:3.12-slim

# Avoid Python buffering issues in logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy orchestrator source
COPY . .

# Expose orchestrator HTTP port
EXPOSE 8004

# Start FastAPI orchestrator
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
