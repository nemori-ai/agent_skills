# Docker 环境

本文档介绍 Agent Skills Docker 镜像的预装环境和配置。

## 构建镜像

```bash
docker build -t agent-skills:latest -f docker_config/Dockerfile .
```

---

## 预装工具

### 系统工具

| 工具 | 用途 |
|------|------|
| git | 版本控制 |
| curl | HTTP 请求 |
| jq | JSON 处理 |
| ripgrep (rg) | 快速搜索 |
| poppler-utils | PDF 转图片（pdftotext, pdftoppm） |
| qpdf | PDF 处理和修复 |
| imagemagick | 图像处理 |
| Node.js 22.x | JavaScript 运行时 |

### Python 环境

- Python 3.12+
- uv（包管理器，用于依赖隔离）

### 预装 Python 库

| 库 | 用途 |
|------|------|
| pypdf | PDF 读写 |
| pdfplumber | PDF 文本提取 |
| pandas | 数据处理 |
| pillow | 图像处理 |
| requests | HTTP 请求 |
| httpx | 异步 HTTP |
| pyyaml | YAML 解析 |

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SKILLS_WORKSPACE` | `/workspace` | 工作目录，用户项目挂载位置 |
| `SKILLS_DIR` | `/skills` | 技能目录，技能包存储位置 |
| `PYTHONUNBUFFERED` | `1` | Python 输出不缓冲 |

---

## 目录结构

容器内的标准目录结构：

```
/
├── workspace/      # 用户项目（-v 挂载）
├── skills/         # 技能目录（-v 挂载）
└── app/            # Agent Skills 代码
    └── agent_skills/
        └── skills/ # 内置技能（fallback）
```

---

## 挂载方式

### 方式 1：挂载项目目录（推荐）

```bash
docker run -i --rm \
  -v /path/to/my-project:/workspace \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest
```

- `/workspace`：用户的项目目录
- `/skills`：用户的技能目录（可创建和修改技能）

### 方式 2：挂载用户目录（完全访问）

```bash
docker run -i --rm \
  -v /Users/me:/Users/me \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest
```

Agent 可以使用绝对路径访问用户目录下的任何文件。

### 方式 3：只读挂载

```bash
docker run -i --rm \
  -v /path/to/project:/workspace:ro \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest
```

项目目录只读，技能目录可写。

---

## 网络配置

默认情况下，容器使用主机网络：

```bash
docker run -i --rm --network host \
  -v /workspace:/workspace \
  agent-skills:latest
```

如果需要限制网络访问：

```bash
docker run -i --rm --network none \
  -v /workspace:/workspace \
  agent-skills:latest
```

---

## 资源限制

### 内存限制

```bash
docker run -i --rm -m 2g \
  -v /workspace:/workspace \
  agent-skills:latest
```

### CPU 限制

```bash
docker run -i --rm --cpus 2 \
  -v /workspace:/workspace \
  agent-skills:latest
```

---

## 调试容器

### 进入容器 shell

```bash
docker run -it --rm \
  -v /workspace:/workspace \
  agent-skills:latest /bin/bash
```

### 查看已安装的包

```bash
docker run --rm agent-skills:latest pip list
```

### 测试工具可用性

```bash
docker run --rm agent-skills:latest which python uv git rg
```

---

## 自定义镜像

如果需要额外的工具或库，可以基于 `agent-skills:latest` 创建自定义镜像：

```dockerfile
FROM agent-skills:latest

# 安装额外的系统工具
RUN apt-get update && apt-get install -y \
    your-tool \
    && rm -rf /var/lib/apt/lists/*

# 安装额外的 Python 库
RUN pip install your-package
```

构建自定义镜像：

```bash
docker build -t my-agent-skills:latest -f MyDockerfile .
```

---

## 常见问题

### 权限问题

如果遇到文件权限问题，可以指定用户：

```bash
docker run -i --rm -u $(id -u):$(id -g) \
  -v /workspace:/workspace \
  agent-skills:latest
```

### 找不到命令

确保镜像是最新版本：

```bash
docker build --no-cache -t agent-skills:latest -f docker_config/Dockerfile .
```

### 容器启动慢

首次启动可能较慢（需要创建虚拟环境），后续启动会使用缓存。

