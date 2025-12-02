#!/usr/bin/env python3
"""判断两个整数是否互素的脚本

用法：
    python scripts/main.py <a> <b>

返回：
    在标准输出打印 True 或 False
"""
import argparse
import math
import sys


def are_coprime(a: int, b: int) -> bool:
    """判断两个整数是否互素（最大公约数为 1）。"""
    return math.gcd(a, b) == 1


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="判断两个整数是否互素")
    parser.add_argument("a", type=int, help="第一个整数")
    parser.add_argument("b", type=int, help="第二个整数")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    a, b = args.a, args.b
    result = are_coprime(a, b)
    # 仅打印 True/False，方便被其他工具管道处理
    print("True" if result else "False")
    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        raise SystemExit(main())
    except Exception as e:
        # 打印到 stderr，方便区分正常输出
        print(f"Error: {e}", file=sys.stderr)
        raise
