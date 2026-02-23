# --------------------------
# 1. Base Image
# --------------------------
FROM python:3.11-slim

# --------------------------
# 2. Set working directory
# --------------------------
WORKDIR /app

# --------------------------
# 3. Copy requirements
# --------------------------
COPY requirements.txt .

# --------------------------
# 4. Install dependencies
# --------------------------
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------
# 5. Copy the application code
# --------------------------
COPY app ./app

# --------------------------
# 6. Expose FastAPI port
# --------------------------
EXPOSE 8001

# --------------------------
# 7. Start FastAPI server
# --------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
