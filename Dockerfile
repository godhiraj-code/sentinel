# Use official Python runtime as a parent image
FROM python:3.11-slim-bookworm

# Metadata
LABEL maintainer="Dhiraj Das <dhirajdas.666@gmail.com>"
LABEL version="0.3.0"
LABEL description="The Sentinel - Autonomous Web Testing Agent"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # Sentinel options
    SENTINEL_HEADLESS=true \
    # Fix for some browser issues in container
    QT_QPA_PLATFORM=offscreen

# Set working directory
WORKDIR /app

# Install system dependencies (Chrome + Tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    unzip \
    curl \
    git \
    build-essential \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxtst6 \
    libxss1 \
    libasound2 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome Stable
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install dependencies and the package
RUN pip install --upgrade pip \
    && pip install ".[full]"

# Create a volume for reports
VOLUME /app/sentinel_reports

# Entrypoint for the CLI
ENTRYPOINT ["sentinel"]

# Default command (can be overridden)
CMD ["--help"]
