# 快速开始：从零创建技能

本指南帮助你在 5 分钟内创建第一个技能包。

## 创建流程概览

```
1. skills_create()     → 创建技能骨架
2. skills_write()      → 添加脚本文件
3. skills_write()      → 添加数据/模板（可选）
4. skills_ls()         → 查看文件结构
5. skills_run()        → 测试运行
```

---

## 第一步：创建技能骨架

使用 `skills_create` 创建技能的基础结构：

```python
skills_create(
    name="my-analyzer",
    description="分析数据文件并生成报告",
    instructions="# 数据分析器\n\n## 使用方法\n运行 `skills_run(name=\"my-analyzer\", command=\"python scripts/analyze.py <file>\")`"
)
```

### 命名规范

| 规则 | 正确示例 | 错误示例 |
|------|----------|----------|
| 使用小写字母 | `code-reviewer` | `Code-Reviewer` |
| 用连字符分隔单词 | `data-analyzer` | `dataAnalyzer` |
| 可包含数字 | `pdf2image` | `pdf_to_image` |

---

## 第二步：添加脚本

使用 `skills_write` 添加可执行脚本：

```python
skills_write(
    path="skills/my-analyzer/scripts/analyze.py",
    content='''#!/usr/bin/env python3
"""数据分析脚本"""
import sys
import json

def analyze(filepath):
    with open(filepath) as f:
        data = json.load(f)
    # 分析逻辑...
    print(f"分析了 {len(data)} 条记录")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: analyze.py <file>")
        sys.exit(1)
    analyze(sys.argv[1])
'''
)
```

> **提示**：当你向 `scripts/` 目录添加 `.py` 文件时，系统会自动生成 `pyproject.toml` 用于依赖管理。

---

## 第三步：添加数据/模板（可选）

如果技能需要模板或配置文件：

```python
skills_write(
    path="skills/my-analyzer/data/report_template.md",
    content="# 分析报告\n\n日期: {{date}}\n\n## 结果\n{{results}}"
)
```

---

## 第四步：查看和验证

确认文件结构正确：

```python
# 查看技能目录结构
skills_ls(path="skills/my-analyzer")

# 读取特定文件内容
skills_read(path="skills/my-analyzer/scripts/analyze.py")
```

期望看到类似结构：
```
my-analyzer/
├── SKILL.md
├── scripts/
│   ├── analyze.py
│   └── pyproject.toml  (自动生成)
└── data/
    └── report_template.md
```

---

## 第五步：测试运行

执行脚本验证功能：

```python
skills_run(name="my-analyzer", command="python scripts/analyze.py /workspace/sample.json")
```

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| 依赖缺失 | 编辑 `scripts/pyproject.toml` 添加依赖 |
| 脚本执行失败 | 检查路径、参数是否正确 |
| 权限问题 | 确保脚本有执行权限 |

---

## 下一步

- 📝 **完善文档**：阅读 [SKILL.md 编写模板](skillmd-template.md)
- 🔧 **添加更多脚本**：阅读 [脚本编写规范](script-guidelines.md)
- 📚 **参考完整案例**：阅读 [完整示例](full-example.md)

