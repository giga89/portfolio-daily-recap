# Use python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (commented out for faster builds when not needed)
# We install chromium and its dependencies. 
# If other browsers are needed, add 'firefox' or 'webkit'.
# RUN playwright install --with-deps chromium

# Copy project files
COPY . .

# Create output directory
RUN mkdir -p output

# Default entry command
CMD ["python", "src/data_collector.py"]
