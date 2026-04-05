# Use the official Python slim image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install system dependencies (if any are needed for Google APIs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


ARG UID=1000
ARG GID=1000

RUN groupadd -f -g ${GID} worker && \
    useradd -m -u ${UID} -g ${GID} -o worker

USER worker
ENV APP_DIR=/home/worker/source
WORKDIR ${APP_DIR}

COPY --chown=worker:worker . ${APP_DIR}


EXPOSE 8000

CMD ["sh", "./scripts/start_container.sh"]
