# Agent Skills

一个为 AI Agent 提供的全栈 Skills 系统，通过 MCP Server 暴露精简的工具接口。

## 功能特性

- **极简工具集**: 仅 5 个工具，以 `bash` 为主要入口，减少 prompt 长度
- **渐进式披露**: Skills 作为 MCP Resource 暴露，预加载元数据，按需读取内容
- **安全沙箱**: 基于 workspace 的路径限制、命令黑名单、文件大小限制
- **MCP 协议**: 标准 MCP Server 接口，可与任何支持 MCP 的 AI 系统集成

## 安装

```bash
# 在 omne-next 项目中
uv sync

# 或单独安装
uv add agent-skills
```

## 快速开始

### 启动 MCP Server

```bash
# 使用当前目录作为 workspace
agent-skills-server

# 指定 workspace
agent-skills-server --workspace /path/to/project

# 只读模式
agent-skills-server --read-only

# 添加额外的 skills 目录
agent-skills-server --skills-dir /path/to/skills
```

### 在代码中使用

```python
from agent_skills.sandbox import Sandbox, SandboxConfig
from agent_skills.core import Executor, SkillManager

# 创建沙箱
config = SandboxConfig(workspace_root="/path/to/workspace")
sandbox = Sandbox(config)

# 使用 Executor 执行命令
executor = Executor(sandbox)
result = await executor.bash("ls -la")
print(result.stdout)

# 使用 SkillManager 发现技能
skill_manager = SkillManager(sandbox)
skills = skill_manager.discover_skills()
for skill in skills:
    print(f"{skill.name}: {skill.description}")
```

## MCP 工具列表

Agent Skills 提供 **5 个精简工具**：

### bash - 主要工具

执行任意 shell 命令，这是最核心的工具。

```python
# 文件操作
bash("ls -la")                          # 列出文件
bash("cat main.py")                     # 读取文件
bash("head -n 20 main.py")              # 读取前 20 行
bash("grep -rn 'TODO' src/")            # 搜索内容
bash("find . -name '*.py'")             # 查找文件

# 文件编辑
bash("echo 'content' > file.txt")       # 写入文件
bash("echo 'more' >> file.txt")         # 追加内容
bash("sed -i '' 's/old/new/g' file.txt")  # 替换 (macOS)
bash("sed -i 's/old/new/g' file.txt")     # 替换 (Linux)

# 目录操作
bash("mkdir -p path/to/dir")            # 创建目录
bash("rm -rf dir/")                     # 删除目录
bash("cp -r src/ dst/")                 # 复制
bash("mv old.txt new.txt")              # 移动/重命名

# 执行脚本
bash("python script.py", timeout=60)    # 运行 Python
bash("npm install", cwd="frontend")     # 指定工作目录
```

### bg - 后台执行

```python
bg("python server.py")                  # 启动后台进程
bg("npm run dev", cwd="frontend")       # 启动开发服务器
```

### jobs - 查看后台任务

```python
jobs()                                  # 列出所有后台任务
```

### kill - 终止进程

```python
kill(12345)                             # 发送 SIGTERM
kill(12345, signal=9)                   # 发送 SIGKILL (强制终止)
```

### skill - 技能管理

```python
skill("list")                           # 列出所有技能（name + description）
skill("list", verbose=True)             # 详细列表（含 URI 和 Path）
skill("create", name="my-skill",        # 创建新技能
      description="Does X",
      instructions="# Instructions...")
skill("validate", path="./my-skill")    # 验证技能格式
```

## MCP Resources - 技能自动暴露

Skills 作为 MCP Resource **自动暴露**给 Agent，实现真正的渐进式披露：

1. **启动时自动暴露**: 所有 skill 的 name 和 description 在 `list_resources()` 中可见
2. **按需读取内容**: `read_resource("skill://skill-name")` 读取完整 SKILL.md

```
Agent 连接 MCP Server 时自动获取:
┌─────────────────────────────────────────────────────────────────┐
│  list_resources() 返回:                                         │
│                                                                  │
│  skill://skill-creator                                          │
│    name: skill-creator                                          │
│    description: 用于创建新技能的元技能，扩展 Agent 的能力边界      │
│                                                                  │
│  skill://code-reviewer                                          │
│    name: code-reviewer                                          │
│    description: 代码审查和质量分析                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓ Agent 判断需要时
┌─────────────────────────────────────────────────────────────────┐
│  read_resource("skill://skill-creator")                         │
│  → 返回完整 SKILL.md 内容（~2000 字符）                          │
└─────────────────────────────────────────────────────────────────┘
```

**无需调用 `skill("list")`**，Agent 启动时就能看到所有可用技能！

这种设计的好处：
- Agent 启动时自动感知所有可用能力
- 减少 token 消耗（只预加载 name/description）
- Agent 按需获取详细指令
- 符合 Claude Skills 官方设计理念

## Skill 格式

Skills 遵循 Claude 官方规范，使用 YAML frontmatter + Markdown：

```markdown
---
name: my-skill
description: What this skill does and when to use it
---

# My Skill

## Overview
[What this skill does]

## Instructions
[How to use this skill]

## Examples
[Concrete examples]
```

## 安全机制

### 路径限制
- 所有文件操作限制在 workspace 目录内
- 自动阻止路径遍历攻击 (`../`)
- 支持自定义黑名单

### 命令安全
- 内置危险命令黑名单：
  - 破坏性命令: `rm -rf /`, `mkfs`, `dd if=/dev/zero`
  - 权限提升: `sudo`, `su`, `doas`
  - 系统控制: `shutdown`, `reboot`
  - Fork bomb 等
- 可配置超时限制
- 可选的网络访问控制

### 默认文件黑名单
- `.git` - Git 目录
- `.env`, `.env.*` - 环境变量文件
- `*.pem`, `*.key` - 密钥文件
- `*_secret*`, `*password*` - 敏感文件

## 配置选项

```python
from agent_skills.sandbox import SandboxConfig

config = SandboxConfig(
    # 工作目录
    workspace_root="/path/to/workspace",
    
    # 文件黑名单模式
    blacklist=[".git", ".env", "*.key"],
    
    # 命令黑名单
    command_blacklist=["rm -rf /", "sudo"],
    
    # 是否允许写操作
    allow_write=True,
    
    # 是否允许网络访问
    allow_network=False,
    
    # 最大文件大小 (bytes)
    max_file_size=10 * 1024 * 1024,  # 10 MB
)
```

## 内部 API

除了 MCP 工具，还可以直接使用内部模块：

```python
from agent_skills.core import FileSystem, Editor, Executor, SkillManager

# FileSystem - 文件操作
fs = FileSystem(sandbox)
fs.cat("main.py")
fs.ls("src", long=True)
fs.grep("TODO", "src", recursive=True)

# Editor - 文件编辑
editor = Editor(sandbox)
editor.sed("file.py", "old", "new", global_replace=True)
editor.write("new.txt", "content")
editor.append("log.txt", "new line\n")

# SkillManager - 技能发现
skill_manager = SkillManager(sandbox)
skills = skill_manager.discover_skills()  # 获取所有技能元数据
skill = skill_manager.find_skill("skill-creator")  # 查找特定技能
content = skill_manager.read_skill_content("skill-creator")  # 读取完整内容
```

## 开发

```bash
# 运行测试
cd agent_skills
pytest tests/ -v

# 运行特定测试
pytest tests/test_executor.py -v
```

## License

Apache 2.0
