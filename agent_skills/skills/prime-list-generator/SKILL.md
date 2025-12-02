---
description: 输入整数 n，输出所有小于 n 的质数列表
name: prime-list-generator
---

# prime-list-generator 技能

## 概述
给定一个正整数 n（n > 1），输出所有 **小于 n** 的质数，以空格分隔或逐行输出。适合需要快速生成素数表的场景。

## 使用方法
在本技能目录中运行以下命令（由 Agent 通过 `skills_run` 调用）：

```bash
python scripts/primes.py <n>
```

- `<n>`：大于 1 的正整数
- 输出：所有小于 n 的质数，按从小到大顺序，以空格分隔

## 输入约定
- n 必须是整数
- n <= 1 时，不输出任何质数，仅提示信息
- 如果传入的不是合法整数，脚本会打印错误信息并以非 0 状态码退出

## 实现说明
- 使用埃拉托斯特尼筛法（Sieve of Eratosthenes）生成质数
- 时间复杂度约为 O(n log log n)，适合中等规模 n（例如 n <= 10^7）

## 示例

### 示例 1
```bash
python scripts/primes.py 10
```
输出：
```text
2 3 5 7
```

### 示例 2
```bash
python scripts/primes.py 2
```
输出：
```text
# no primes less than 2
```

### 示例 3（非法输入）
```bash
python scripts/primes.py hello
```
输出（示例）：
```text
Error: n must be an integer, got 'hello'
```