# Use Python base image
FROM python:3.11-slim

# Install Chrome and Xvfb
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set display for Xvfb
ENV DISPLAY=:99

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot.py .

# Create writable directories
RUN mkdir -p /tmp/extracted /tmp/.cache/seleniumbase

# Set permissions
ENV HOME=/tmp
ENV SELENIUMBASE_CONFIG_DIR=/tmp/.cache/seleniumbase

# Run script with Xvfb
CMD Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 & python bot.py