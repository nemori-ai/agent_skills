#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""计算两个整数的最大公约数（GCD）。

用法：
    python scripts/gcd.py A B
或：
    echo "A B" | python scripts/gcd.py

如果同时提供命令行参数和标准输入，则优先使用命令行参数。
"""

import sys
import math


def parse_args_or_stdin():
    """从命令行参数或标准输入读取两个整数。"""
    # 优先使用命令行参数
    if len(sys.argv) >= 3:
        try:
            a = int(sys.argv[1])
            b = int(sys.argv[2])
            return a, b
        except ValueError:
            print("错误：命令行参数必须是整数", file=sys.stderr)
            sys.exit(1)

    # 如果没有足够的命令行参数，则尝试从标准输入读取
    data = sys.stdin.read().strip()
    if not data:
        print("用法：python scripts/gcd.py A B 或通过标准输入提供两个整数，例如：echo \"12 18\" | python scripts/gcd.py", file=sys.stderr)
        sys.exit(1)

    parts = data.split()
    if len(parts) < 2:
        print("错误：需要提供两个整数，用空格分隔", file=sys.stderr)
        sys.exit(1)

    try:
        a = int(parts[0])
        b = int(parts[1])
        return a, b
    except ValueError:
        print("错误：输入必须是整数", file=sys.stderr)
        sys.exit(1)


def gcd(a: int, b: int) -> int:
    """返回 a 和 b 的最大公约数（非负整数）。"""
    return math.gcd(a, b)


if __name__ == "__main__":
    a, b = parse_args_or_stdin()
    result = gcd(a, b)
    print(result)
