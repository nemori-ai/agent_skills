---
description: 计算两个整数的最大公约数（GCD）
name: gcd-calculator
---

# gcd-calculator 技能

## 概述
该技能用于计算两个整数的最大公约数（Greatest Common Divisor, GCD）。

## 使用方法
在该技能目录下运行脚本：

```bash
python scripts/gcd.py A B
```

其中 `A` 和 `B` 是要计算最大公约数的两个整数（可以为正负整数，结果总是非负）。

也可以从标准输入读取两个数：

```bash
echo "12 18" | python scripts/gcd.py
```

## 输入说明
- 命令行参数：两个整数 A 和 B
- 或标准输入：一行内包含两个整数，以空格分隔

## 输出说明
- 输出一个整数，即这两个数的最大公约数

## 示例
```bash
python scripts/gcd.py 12 18
# 输出：6

python scripts/gcd.py -8 12
# 输出：4
```