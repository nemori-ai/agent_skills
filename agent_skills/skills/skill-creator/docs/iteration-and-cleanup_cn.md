# 脚本迭代与清理规范

在开发技能脚本时，你可能会经历多次迭代——第一个版本可能因为依赖问题、复杂度过高或其他原因无法正常执行。

**核心原则：当你创建了替代脚本后，必须清理掉失败的旧脚本。**

---

## ❌ 错误做法

```
my-skill/scripts/
├── convert.py              # 第一版，依赖问题无法执行
├── convert_v2.py           # 第二版，仍然有问题
├── convert_simple.py       # 第三版，可以工作
└── pyproject.toml
```

**问题**：
- 目录混乱，难以维护
- 后续使用者不知道该用哪个脚本
- SKILL.md 中的说明可能与实际可用脚本不符

---

## ✅ 正确做法

### 方式一：删除失败的脚本

当新脚本验证成功后，删除所有失败版本：

```python
# 删除失败的脚本
skills_bash(command="rm scripts/convert.py scripts/convert_v2.py", cwd="skills/my-skill")
```

### 方式二：重命名为主脚本

如果原本有一个"主脚本名"，将成功版本重命名：

```python
# 将成功的脚本重命名为主脚本名
skills_bash(command="mv scripts/convert_simple.py scripts/convert.py", cwd="skills/my-skill")

# 删除旧的失败版本（如果有）
skills_bash(command="rm -f scripts/convert_v2.py", cwd="skills/my-skill")
```

### 方式三：更新 SKILL.md

如果决定保留新的脚本名，确保更新文档：

```python
# 读取当前 SKILL.md
skills_read(path="skills/my-skill/SKILL.md")

# 修改文档中的命令示例，指向正确的脚本
skills_write(path="skills/my-skill/SKILL.md", content="""...(更新后的内容)""")
```

---

## 清理检查清单

在完成技能创建后，执行以下检查：

### 1. 检查文件结构

```python
skills_ls(path="skills/<name>/scripts")
```

确认：
- [ ] 只包含可用的脚本
- [ ] 没有 `_old`、`_backup`、`_v2`、`_simple` 等临时命名的残留文件

### 2. 检查文档一致性

```python
skills_read(path="skills/<name>/SKILL.md")
```

确认：
- [ ] 文档中的命令示例指向实际存在的脚本
- [ ] 参数说明与脚本实际参数一致

### 3. 验证脚本可执行

```python
skills_run(name="<name>", command="python scripts/main.py --help")
```

确认：
- [ ] 脚本可以正常执行
- [ ] 帮助信息正确显示

---

## 为什么这很重要？

技能包是**可复用的能力模块**。一个整洁、文档准确的技能包：

| 好处 | 说明 |
|------|------|
| 易于理解 | 其他 Agent 或用户能快速上手 |
| 避免困惑 | 不会误执行失败的脚本 |
| 专业规范 | 体现良好的开发习惯 |
| 便于维护 | 后续修改时不会被历史文件干扰 |

---

## 迭代开发建议

如果预期脚本需要多次迭代：

1. **先用简单版本验证思路**：从最简单的实现开始
2. **验证成功后再增加复杂度**：逐步添加功能
3. **及时清理**：每次迭代成功后立即清理旧版本
4. **保持单一入口**：最终只保留一个主脚本

