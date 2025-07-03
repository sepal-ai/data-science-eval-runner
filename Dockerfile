# Data Science Agent Evaluation Environment
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV WORKDIR=/workdir

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /workdir

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY ds_runner/ ./ds_runner/
COPY problems/ ./problems/
COPY config.yaml ./

# Install uv for faster dependency management
RUN pip install uv

# Install dependencies
RUN uv pip install --system -e .

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash model
RUN chown -R model:model /workdir

# Set up data directory
RUN mkdir -p /workdir/data && chown model:model /workdir/data

# Expose port for potential web interfaces
EXPOSE 8000

# Default to model user
USER model

# Default command
CMD ["python", "-m", "ds_runner", "validate-setup"] 