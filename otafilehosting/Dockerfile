FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY main.py /app/main.py
COPY requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create OTA directory
RUN mkdir -p /app/OTA

# Expose the port
EXPOSE 5004

# Run the application
CMD ["python", "main.py"]
