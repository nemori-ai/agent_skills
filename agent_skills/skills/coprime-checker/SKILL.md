---
description: 判断两个整数是否互素（最大公约数为 1）
name: coprime-checker
---

---
name: coprime-checker
description: 判断两个整数是否互素（最大公约数为 1）
---

# 互素判断器（Coprime Checker）

## 概述
本技能用于判断两个整数是否互素。互素的定义是：两个整数的最大公约数为 1。

## 依赖
- Python 3
- 仅使用标准库，无额外依赖

## 使用方法

### 基本用法
在技能环境中运行：
```bash
skills_run(name="coprime-checker", command="python scripts/main.py <a> <b>")
```
其中 `<a>` 和 `<b>` 为要判断的两个整数（可以为正数、负数或零）。

示例：
```bash
skills_run(name="coprime-checker", command="python scripts/main.py 8 15")
```
输出：
```text
True
```
表示 8 和 15 互素。

## 参数说明
- `a`：第一个整数
- `b`：第二个整数

## 脚本说明

| 脚本 | 功能 |
|------|------|
| `scripts/main.py` | 主脚本，计算两数最大公约数并输出是否互素 |

## 示例

1. 互素示例：
```bash
skills_run(name="coprime-checker", command="python scripts/main.py 14 25")
```
输出：
```text
True
```

2. 非互素示例：
```bash
skills_run(name="coprime-checker", command="python scripts/main.py 12 18")
```
输出：
```text
False
```

## 注意事项
- 非整数输入会报错提示。
- 如果两数中有 0，则只有在其中一个为 ±1 时才算互素（因为 gcd(0, n) = |n|）。
