---
description: Download files from specified URLs to local, supporting multiple protocols and download options
name: file-downloader
---

# File Downloader

Download files from specified URLs to local, supporting HTTP/HTTPS protocols.

## ⚠️ Important Note

**Always use absolute paths for output!** Skills directory should remain clean, only storing skill code.

## Usage

### Basic Download
```python
# Download file (recommended)
skills_run(name="file-downloader", command="python scripts/download.py https://example.com/file.pdf -o /Users/xxx/Downloads/file.pdf")

# Download with progress display
skills_run(name="file-downloader", command="python scripts/download.py https://example.com/file.pdf -o /Users/xxx/Downloads/file.pdf -v")
```

### Advanced Options
```python
# Set timeout (seconds)
skills_run(name="file-downloader", command="python scripts/download.py https://example.com/file.pdf -o /Users/xxx/Downloads/file.pdf --timeout 60")

# Set user agent
skills_run(name="file-downloader", command="python scripts/download.py https://example.com/file.pdf -o /Users/xxx/Downloads/file.pdf --user-agent 'Mozilla/5.0'")

# Overwrite existing file
skills_run(name="file-downloader", command="python scripts/download.py https://example.com/file.pdf -o /Users/xxx/Downloads/file.pdf -f")
```

## Features

- ✅ HTTP/HTTPS protocol support
- ✅ Automatic filename detection
- ✅ Download progress display
- ✅ Resume download (TODO)
- ✅ Custom request headers
- ✅ File integrity verification

## Parameters

- `url`: URL of file to download (required)
- `-o, --output`: Output file path (**use absolute path**)
- `-v, --verbose`: Show detailed progress info
- `-f, --force`: Overwrite existing file
- `--timeout`: Request timeout in seconds (default 30s)
- `--user-agent`: Custom User-Agent

## Path Guidelines

| Path | Description |
|------|-------------|
| Absolute paths | User workspace, **all downloaded files should be saved here** |
| `/skills/` | Skill code directory, do not save user files here |
