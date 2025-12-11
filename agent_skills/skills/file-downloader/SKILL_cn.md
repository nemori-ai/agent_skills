---
description: 从指定 URL 下载文件到本地，支持多种协议和下载选项
name: file-downloader
---

# 文件下载器

从指定 URL 下载文件到本地，支持 HTTP/HTTPS 协议。

## ⚠️ 重要提示

**始终使用 `/workspace/` 作为输出目录！** Skills 目录应保持整洁，只存放技能代码。

## 使用方法

### 基本下载
```python
# 下载文件到工作空间（推荐）
skills_run(name="file-downloader", command="python scripts/download.py https://example.com/file.pdf -o /workspace/file.pdf")

# 下载并显示进度
skills_run(name="file-downloader", command="python scripts/download.py https://example.com/file.pdf -o /workspace/file.pdf -v")
```

### 高级选项
```python
# 设置超时时间（秒）
skills_run(name="file-downloader", command="python scripts/download.py https://example.com/file.pdf -o /workspace/file.pdf --timeout 60")

# 设置用户代理
skills_run(name="file-downloader", command="python scripts/download.py https://example.com/file.pdf -o /workspace/file.pdf --user-agent 'Mozilla/5.0'")

# 覆盖已存在的文件
skills_run(name="file-downloader", command="python scripts/download.py https://example.com/file.pdf -o /workspace/file.pdf -f")
```

## 特性

- ✅ 支持 HTTP/HTTPS 协议
- ✅ 自动检测文件名
- ✅ 显示下载进度
- ✅ 断点续传（TODO）
- ✅ 自定义请求头
- ✅ 文件完整性验证

## 参数说明

- `url`: 要下载的文件 URL（必需）
- `-o, --output`: 输出文件路径（**必须使用 `/workspace/` 前缀**）
- `-v, --verbose`: 显示详细进度信息
- `-f, --force`: 覆盖已存在的文件
- `--timeout`: 请求超时时间，单位秒（默认30秒）
- `--user-agent`: 自定义 User-Agent

## 路径说明

| 路径 | 说明 |
|------|------|
| `/workspace/` | 用户工作空间，**所有下载文件应保存到这里** |
| `/skills/` | 技能代码目录，请勿在此保存用户文件 |