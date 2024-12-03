FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .


# Default command can be overridden in docker-compose for specific services
CMD ["celery", "-A", "healthcheck", "worker", "--loglevel=info"]
