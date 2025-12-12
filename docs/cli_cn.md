# CLI 命令参考

Agent Skills 提供 `agent-skills` 命令行工具，用于从 Git 仓库安装、卸载和管理 skills。

## 安装

CLI 工具随 `agent-skills` 包一起安装：

```bash
uv sync
```

安装后即可使用 `agent-skills` 命令。

---

## 命令概览

| 命令 | 功能 |
|------|------|
| `agent-skills install <url>` | 从 Git 仓库安装 skill |
| `agent-skills uninstall <name>` | 卸载已安装的 skill |
| `agent-skills list` | 列出所有 skills |
| `agent-skills sync-claude` | 将 Claude Code 的个人 skills 同步到 agent-skills |

---

## 全局选项

| 选项 | 说明 |
|------|------|
| `--dir, -d <path>` | 指定 skills 目录（默认：`~/.agent-skills/skills/`） |
| `--version, -v` | 显示版本信息 |
| `--help, -h` | 显示帮助信息 |

---

## install - 安装 Skill

从 Git 仓库安装 skill 到本地目录。

### 语法

```bash
agent-skills install <url> [options]
```

### 参数

| 参数 | 说明 |
|------|------|
| `url` | Git 仓库 URL（必需） |

### 选项

| 选项 | 说明 |
|------|------|
| `--ref, -r <ref>` | Git 引用（分支、标签或提交哈希） |
| `--name, -n <name>` | 自定义 skill 名称（仅适用于单 skill 仓库） |
| `--path, -p <path>` | 仓库内的子目录路径（用于从大型仓库安装特定 skill） |
| `--dir, -d <path>` | 安装目录 |

### 示例

```bash
# 基本安装
agent-skills install https://github.com/user/my-skill.git

# 安装指定版本
agent-skills install https://github.com/user/my-skill.git --ref v1.0.0

# 安装指定分支
agent-skills install https://github.com/user/my-skill.git --ref main

# 使用自定义名称
agent-skills install https://github.com/user/my-skill.git --name custom-skill

# 安装到自定义目录
agent-skills install https://github.com/user/my-skill.git --dir ./my-project/skills

# 从大型仓库安装特定子目录的 skill（使用 sparse checkout，只下载需要的文件）
agent-skills install https://github.com/metabase/metabase.git --path .claude/skills/clojure-review
```

### 仓库结构支持

**单 Skill 仓库**：根目录直接包含 `SKILL.md`

```
my-skill/
├── SKILL.md
├── scripts/
│   └── main.py
└── data/
```

**多 Skill 仓库**：根目录包含多个 skill 子目录

```
skills-collection/
├── skill-a/
│   ├── SKILL.md
│   └── scripts/
├── skill-b/
│   ├── SKILL.md
│   └── scripts/
└── README.md
```

安装多 skill 仓库时，所有包含 `SKILL.md` 的子目录都会被安装。

### 从大型仓库安装特定 Skill

有些项目（如 [metabase](https://github.com/metabase/metabase)）将 skills 放在仓库的子目录中。使用 `--path` 参数可以只下载需要的部分，而不是克隆整个仓库：

```bash
# 只安装 metabase 仓库中的 clojure-review skill
agent-skills install https://github.com/metabase/metabase.git --path .claude/skills/clojure-review

# 安装多个 skills（指定包含多个 skill 的父目录）
agent-skills install https://github.com/metabase/metabase.git --path .claude/skills
```

**工作原理**：使用 Git sparse checkout 技术，只下载指定路径的文件，大幅减少下载量和安装时间。

**注意**：`--path` 参数需要的是仓库内的相对路径，不是 GitHub 网页 URL。例如：

| 网页 URL | 正确的 --path 参数 |
|----------|-------------------|
| `https://github.com/metabase/metabase/tree/master/.claude/skills/clojure-review` | `.claude/skills/clojure-review` |
| `https://github.com/user/repo/tree/main/skills/my-skill` | `skills/my-skill` |

---

## uninstall - 卸载 Skill

从 skills 目录中删除已安装的 skill。

### 语法

```bash
agent-skills uninstall <name> [options]
```

### 参数

| 参数 | 说明 |
|------|------|
| `name` | 要卸载的 skill 名称（必需） |

### 选项

| 选项 | 说明 |
|------|------|
| `--dir, -d <path>` | skills 目录 |

### 示例

```bash
# 卸载 skill
agent-skills uninstall my-skill

# 从自定义目录卸载
agent-skills uninstall my-skill --dir ./my-project/skills
```

---

## list - 列出 Skills

列出 skills 目录中的所有 skills。

### 语法

```bash
agent-skills list [options]
```

### 选项

| 选项 | 说明 |
|------|------|
| `--installed, -i` | 只显示通过 CLI 安装的 skills |
| `--dir, -d <path>` | skills 目录 |

### 示例

```bash
# 列出所有 skills
agent-skills list

# 只列出通过 CLI 安装的 skills
agent-skills list --installed

# 列出自定义目录的 skills
agent-skills list --dir ./my-project/skills
```

### 输出示例

```
Skills in /Users/xxx/.agent-skills/skills:

  my-skill [installed]
    A useful skill for automation
    Source: https://github.com/user/my-skill.git @ v1.0.0

  pdf
    PDF processing toolkit

  skill-creator
    Meta-skill for creating new skills

Total: 3 skill(s), 1 installed via CLI
```

---

## sync-claude - 同步 Claude Code 个人 Skills

将 Claude Code 用户在 `~/.claude/skills/` 下的个人 skills 同步到 agent-skills 的 skills 目录中，方便复用 Claude 的生态（例如你已经在 Claude Code 里维护了一套技能）。

### 语法

```bash
agent-skills sync-claude [options]
```

### 选项

| 选项 | 说明 |
|------|------|
| `--source, -s <path>` | Claude skills 目录（默认：`~/.claude/skills/`） |
| `--overwrite` | 如果目标目录已存在同名 skill，则覆盖 |
| `--dry-run` | 仅显示将执行的操作，不实际复制文件 |
| `--dir, -d <path>` | agent-skills 的 skills 目录（同步目标目录） |

### 示例

```bash
# 同步 Claude Code 个人 skills 到默认目录
agent-skills sync-claude

# 同步到项目本地 skills 目录（例如给 MCP 挂载用）
agent-skills sync-claude --dir ./skills

# 覆盖同名技能
agent-skills sync-claude --overwrite

# 只预览，不做实际复制
agent-skills sync-claude --dry-run
```

### 同步规则

- 会扫描 `--source` 目录下的**一级子目录**
- 仅同步包含 `SKILL.md` 的目录
- 同步后会写入 `.installed.json` 元数据，`source` 会标记为 `claude:<source_dir>`，用于追踪来源

---

## 安装目录

### 默认位置

Skills 默认安装到 `~/.agent-skills/skills/`，这与 MCP 配置中推荐的挂载路径一致：

```json
{
  "mcpServers": {
    "agent-skills": {
      "args": ["-v", "~/.agent-skills/skills:/skills", ...]
    }
  }
}
```

### 自定义位置

使用 `--dir` 参数可以指定不同的安装目录：

```bash
# 安装到项目本地目录
agent-skills install https://github.com/user/skill.git --dir ./skills

# 安装到其他位置
agent-skills install https://github.com/user/skill.git --dir /path/to/skills
```

---

## 安装元数据

通过 CLI 安装的 skill 会在目录下创建 `.installed.json` 文件，记录安装信息：

```json
{
  "source": "https://github.com/user/my-skill.git",
  "ref": "v1.0.0",
  "installed_at": "2025-01-15T10:30:00+00:00",
  "commit": "abc1234def5",
  "path": ".claude/skills/my-skill"
}
```

> `path` 字段仅在使用 `--path` 参数安装时存在。

这些信息用于：
- 区分手动添加的 skills 和通过 CLI 安装的 skills
- 记录安装来源和版本
- 支持未来的更新功能

---

## 常见问题

### Q: 安装失败，提示 "git command not found"

**A**: 请确保系统已安装 Git：

```bash
# macOS
brew install git

# Ubuntu/Debian
sudo apt install git
```

### Q: 如何更新已安装的 skill？

**A**: 目前需要先卸载再重新安装：

```bash
agent-skills uninstall my-skill
agent-skills install https://github.com/user/my-skill.git --ref v2.0.0
```

### Q: skill 安装后没有在 Agent 中显示？

**A**: 请检查：
1. 确保安装目录与 MCP/Middleware 配置的 skills 目录一致
2. 如果使用 MCP，需要重启 MCP Server（重启 Cursor/Claude Desktop）
3. 确保 skill 目录包含有效的 `SKILL.md` 文件

### Q: 如何查看 skill 的详细信息？

**A**: 使用 `skills_read` 工具或直接查看 `SKILL.md`：

```bash
cat ~/.agent-skills/skills/my-skill/SKILL.md
```
