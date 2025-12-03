# Agent Skills MCP Server
# A Docker-based execution environment for AI agent skills

FROM python:3.12-slim

LABEL maintainer="Nemori AI <dev@nemori.ai>"
LABEL description="Agent Skills MCP Server - Execution environment for AI skills"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essential tools
    git \
    curl \
    jq \
    # PDF processing
    poppler-utils \
    qpdf \
    # Image processing
    imagemagick \
    # Text processing
    ripgrep \
    # Build tools (for some Python packages)
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22.x
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
RUN pip install --no-cache-dir uv

# Set up working directories
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY agent_skills ./agent_skills/

# Install the project
RUN uv sync --no-dev

# Pre-install common Python libraries
RUN uv pip install --no-cache-dir \
    # PDF processing
    pypdf \
    pdfplumber \
    # Data processing
    pandas \
    # Image processing
    pillow \
    # HTTP requests
    requests \
    httpx \
    # YAML processing
    pyyaml

# Create workspace and skills directories
RUN mkdir -p /workspace /skills

# Environment variables
ENV SKILLS_WORKSPACE=/workspace
ENV SKILLS_DIR=/skills
ENV PYTHONUNBUFFERED=1

# Set workspace as default working directory
WORKDIR /workspace

# Default command: start MCP server in stdio mode
ENTRYPOINT ["uv", "run", "agent-skills-server"]
CMD ["--quiet"]

