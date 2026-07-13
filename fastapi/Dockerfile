FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# AgentBase Runtime routes traffic to 8080; Render (and others) inject $PORT.
EXPOSE 8080

# Health check endpoint is GET /health (defined in main.py)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
