FROM python:3.12-slim

WORKDIR /app/app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# default (compose overrides command anyway)
CMD ["python", "worker.py"]
