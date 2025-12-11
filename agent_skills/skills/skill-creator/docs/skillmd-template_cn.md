# SKILL.md 编写模板

SKILL.md 是技能的入口文档，告诉使用者这个技能做什么、怎么用。

## 必需结构

### 1. YAML Frontmatter（必需）

文件必须以 YAML frontmatter 开头：

```yaml
---
name: skill-name
description: 简洁的功能描述（一句话说明技能用途）
---
```

**字段说明**：
- `name`：技能唯一标识，必须与目录名一致
- `description`：显示在技能列表中的简介（建议 < 50 字）

---

### 2. 文档正文结构

推荐使用以下结构组织内容：

```markdown
# 技能名称

一两句话概述这个技能的核心功能和适用场景。

## 依赖

- Python 3.12+
- 第三方库：pandas, requests（如有）

## 使用方法

### 基本用法

```
skills_run(name="skill-name", command="python scripts/main.py <args>")
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `<input>` | 输入文件路径 | 必需 |
| `--output`, `-o` | 输出文件路径 | stdout |
| `--verbose`, `-v` | 显示详细信息 | false |

## 脚本说明

| 脚本 | 功能 |
|------|------|
| `scripts/main.py` | 主逻辑脚本 |
| `scripts/helpers.sh` | 辅助工具（可选） |

## 示例

### 输入
```json
{"name": "test", "value": 123}
```

### 命令
```
skills_run(name="skill-name", command="python scripts/main.py input.json -o output.txt")
```

### 输出
```
处理完成：1 条记录
```

## 注意事项

- 输入文件必须是有效的 JSON 格式
- 大文件处理可能需要较长时间
- 不支持嵌套超过 10 层的数据结构
```

---

## 编写要点

### ✅ 好的 SKILL.md

- **开门见山**：第一段说清楚技能做什么
- **命令可复制**：示例命令可以直接使用
- **参数明确**：列出所有参数及其含义
- **有输入输出示例**：让用户知道期望结果

### ❌ 避免的写法

- 冗长的背景介绍
- 缺少可执行的命令示例
- 参数说明不完整
- 没有说明依赖和限制

---

## 模板快速复制

```markdown
---
name: my-skill
description: 一句话描述技能功能
---

# 技能名称

技能的核心功能描述。

## 使用方法

```
skills_run(name="my-skill", command="python scripts/main.py <input>")
```

## 参数说明

- `<input>`：输入文件路径

## 示例

输入：`data.json`
输出：处理结果

## 注意事项

- 注意事项 1
- 注意事项 2
```

