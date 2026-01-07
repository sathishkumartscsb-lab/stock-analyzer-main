# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies (TA-Lib C library requires build tools)
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    wget \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib C library
WORKDIR /tmp
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xvzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
# We install numpy first because TA-Lib python wrapper needs it
RUN pip install --no-cache-dir numpy && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 5000 (standard Flask port)
EXPOSE 5000

# Define environment variables (These should be overridden in deployment dashboard)
ENV FLASK_APP=src/web/app.py
ENV FLASK_ENV=production

# Command to run the application (Using gunicorn for production is better than python app.py)
# We need to run BOTH the web app and the bot? 
# Usually best to split them, but for a simple project, we can run a script that starts both.
# For now, let's Stick to the web app as the primary entrypoint, or create a supervisord config.
# Let's create a simple start script.

# Copy and set permissions for start script
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]
