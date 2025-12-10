#!/usr/bin/env python3
"""测试下载功能的脚本"""
import subprocess
import sys
import os


def test_download():
    """测试下载功能"""
    print("=== 文件下载器测试 ===")
    
    # 测试 URL 列表（公开可用的测试文件）
    test_urls = [
        "https://raw.githubusercontent.com/octocat/Hello-World/master/README",
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "https://filesamples.com/samples/document/txt/sample1.txt",
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n--- 测试 {i}: {url} ---")
        
        try:
            # 执行下载命令
            result = subprocess.run([
                "python", "scripts/download.py", 
                url, 
                "-v", 
                "-o", f"/workspace/test_file_{i}.txt"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ 下载成功")
                print(result.stdout)
            else:
                print("❌ 下载失败")
                print("错误输出:", result.stderr)
                
        except subprocess.TimeoutExpired:
            print("❌ 下载超时")
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_download()