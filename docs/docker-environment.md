# Docker Environment

This document describes the pre-installed environment and configuration of the Agent Skills Docker image.

## Build Image

```bash
docker build -t agent-skills:latest -f docker_config/Dockerfile .
```

---

## Pre-installed Tools

### System Tools

| Tool | Purpose |
|------|---------|
| git | Version control |
| curl | HTTP requests |
| jq | JSON processing |
| ripgrep (rg) | Fast search |
| poppler-utils | PDF to image (pdftotext, pdftoppm) |
| qpdf | PDF processing and repair |
| imagemagick | Image processing |
| Node.js 22.x | JavaScript runtime |

### Python Environment

- Python 3.12+
- uv (package manager for dependency isolation)

### Pre-installed Python Libraries

| Library | Purpose |
|---------|---------|
| pypdf | PDF read/write |
| pdfplumber | PDF text extraction |
| pandas | Data processing |
| pillow | Image processing |
| requests | HTTP requests |
| httpx | Async HTTP |
| pyyaml | YAML parsing |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SKILLS_WORKSPACE` | `/workspace` | Working directory, user project mount location |
| `SKILLS_DIR` | `/skills` | Skills directory, skill package storage location |
| `PYTHONUNBUFFERED` | `1` | Python output not buffered |

---

## Directory Structure

Standard directory structure inside the container:

```
/
├── workspace/      # User project (-v mount)
├── skills/         # Skills directory (-v mount)
└── app/            # Agent Skills code
    └── agent_skills/
        └── skills/ # Built-in skills (fallback)
```

---

## Mount Methods

### Method 1: Mount Project Directory (Recommended)

```bash
docker run -i --rm \
  -v /path/to/my-project:/workspace \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest
```

- `/workspace`: User's project directory
- `/skills`: User's skills directory (can create and modify skills)

### Method 2: Mount User Directory (Full Access)

```bash
docker run -i --rm \
  -v /Users/me:/Users/me \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest
```

Agent can access any file in the user directory using absolute paths.

### Method 3: Read-only Mount

```bash
docker run -i --rm \
  -v /path/to/project:/workspace:ro \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest
```

Project directory is read-only, skills directory is writable.

---

## Network Configuration

By default, the container uses host network:

```bash
docker run -i --rm --network host \
  -v /workspace:/workspace \
  agent-skills:latest
```

If network access needs to be restricted:

```bash
docker run -i --rm --network none \
  -v /workspace:/workspace \
  agent-skills:latest
```

---

## Resource Limits

### Memory Limit

```bash
docker run -i --rm -m 2g \
  -v /workspace:/workspace \
  agent-skills:latest
```

### CPU Limit

```bash
docker run -i --rm --cpus 2 \
  -v /workspace:/workspace \
  agent-skills:latest
```

---

## Debugging Container

### Enter Container Shell

```bash
docker run -it --rm \
  -v /workspace:/workspace \
  agent-skills:latest /bin/bash
```

### View Installed Packages

```bash
docker run --rm agent-skills:latest pip list
```

### Test Tool Availability

```bash
docker run --rm agent-skills:latest which python uv git rg
```

---

## Custom Image

If additional tools or libraries are needed, create a custom image based on `agent-skills:latest`:

```dockerfile
FROM agent-skills:latest

# Install additional system tools
RUN apt-get update && apt-get install -y \
    your-tool \
    && rm -rf /var/lib/apt/lists/*

# Install additional Python libraries
RUN pip install your-package
```

Build custom image:

```bash
docker build -t my-agent-skills:latest -f MyDockerfile .
```

---

## FAQ

### Permission Issues

If you encounter file permission issues, specify user:

```bash
docker run -i --rm -u $(id -u):$(id -g) \
  -v /workspace:/workspace \
  agent-skills:latest
```

### Command Not Found

Ensure image is the latest version:

```bash
docker build --no-cache -t agent-skills:latest -f docker_config/Dockerfile .
```

### Container Starts Slowly

First startup may be slow (needs to create virtual environment), subsequent startups will use cache.
