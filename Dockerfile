FROM python:3.12-slim

# Install system packages and Python dependencies
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y cups libcups2-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Set working directory
WORKDIR /app
COPY . /app

# Create runtime folders
RUN mkdir -p /data/
RUN mkdir -p /data/printjobs

EXPOSE 8080

CMD ["python", "run.py"]