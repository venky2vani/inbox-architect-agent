FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY agent.py config.yaml ./
COPY plugins/ ./plugins/

# Credentials are mounted at runtime, not baked into the image.
VOLUME ["/app/credentials"]

# Default command runs the daily digest.
CMD ["python", "agent.py"]
