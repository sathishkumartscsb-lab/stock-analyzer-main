FROM python:3.10-slim

# Install system dependencies (needed for Pillow/Matplotlib)
RUN apt-get update && apt-get install -y \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Ensure start script is executable
RUN chmod +x start.sh

# Environment variables (Defaults, can be overridden by Render)
ENV PYTHONUNBUFFERED=1

# Run the start script
CMD ["./start.sh"]
