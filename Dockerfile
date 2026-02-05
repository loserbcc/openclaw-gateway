FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# Data volume for SQLite + uploads
VOLUME /app/data

EXPOSE 8770

CMD ["openclaw-gateway"]
