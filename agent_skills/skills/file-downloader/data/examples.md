# 使用示例

## 基本用法

### 1. 下载文件到默认位置
```bash
python scripts/download.py https://example.com/file.pdf
```

### 2. 指定输出文件
```bash
python scripts/download.py https://example.com/document.pdf -o /path/to/save/document.pdf
```

### 3. 显示详细进度
```bash
python scripts/download.py https://example.com/large_file.zip -v
```

### 4. 覆盖已存在的文件
```bash
python scripts/download.py https://example.com/file.pdf -f
```

## 高级用法

### 5. 设置自定义超时时间
```bash
python scripts/download.py https://slow-server.com/file.pdf --timeout 60
```

### 6. 设置自定义 User-Agent
```bash
python scripts/download.py https://example.com/file.pdf --user-agent "MyDownloader/1.0"
```

## 常见用例

### 下载 GitHub 文件
```bash
python scripts/download.py https://raw.githubusercontent.com/user/repo/main/file.txt
```

### 下载 PDF 文档
```bash
python scripts/download.py https://arxiv.org/pdf/1234.5678.pdf -o research_paper.pdf
```

### 下载图片
```bash
python scripts/download.py https://example.com/image.jpg -v
```

## 错误处理

- **404 错误**: 检查 URL 是否正确
- **超时错误**: 增加 `--timeout` 值
- **权限错误**: 检查输出目录是否有写权限
- **文件已存在**: 使用 `-f` 参数强制覆盖

## 支持的协议

- HTTP (http://)
- HTTPS (https://)

## 文件名处理

- 如果不指定 `-o` 参数，将自动从 URL 中提取文件名
- 如果 URL 没有文件名，将使用 'downloaded_file' 作为默认名称