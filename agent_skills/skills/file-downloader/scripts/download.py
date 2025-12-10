#!/usr/bin/env python3
"""从 URL 下载文件到本地"""
import argparse
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path


def get_filename_from_url(url):
    """从 URL 中提取文件名"""
    parsed = urllib.parse.urlparse(url)
    filename = os.path.basename(parsed.path)
    
    # 如果 URL 没有文件名，使用默认名称
    if not filename or '.' not in filename:
        filename = 'downloaded_file'
    
    return filename


def download_file(url, output_path, verbose=False, force=False, timeout=30, user_agent=None):
    """下载文件"""
    
    # 检查输出文件是否已存在
    if os.path.exists(output_path) and not force:
        print(f"错误: 文件已存在 - {output_path}")
        print("使用 -f/--force 参数覆盖已存在的文件")
        sys.exit(1)
    
    # 创建输出目录
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 创建请求对象
        request = urllib.request.Request(url)
        
        # 设置用户代理
        if user_agent:
            request.add_header('User-Agent', user_agent)
        else:
            request.add_header('User-Agent', 'file-downloader/1.0')
        
        if verbose:
            print(f"开始下载: {url}")
            print(f"保存到: {output_path}")
        
        # 下载文件
        with urllib.request.urlopen(request, timeout=timeout) as response:
            # 获取文件大小
            content_length = response.headers.get('Content-Length')
            total_size = int(content_length) if content_length else None
            
            if verbose and total_size:
                print(f"文件大小: {total_size:,} 字节 ({total_size / 1024 / 1024:.1f} MB)")
            
            # 开始下载
            downloaded = 0
            chunk_size = 8192
            
            with open(output_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # 显示进度
                    if verbose:
                        if total_size:
                            percent = (downloaded / total_size) * 100
                            print(f"\r进度: {downloaded:,} / {total_size:,} 字节 ({percent:.1f}%)", end='', flush=True)
                        else:
                            print(f"\r已下载: {downloaded:,} 字节", end='', flush=True)
            
            if verbose:
                print()  # 换行
        
        print(f"下载完成: {output_path}")
        print(f"文件大小: {downloaded:,} 字节")
        
        return True
        
    except urllib.error.HTTPError as e:
        print(f"HTTP 错误: {e.code} - {e.reason}", file=sys.stderr)
        return False
    except urllib.error.URLError as e:
        print(f"URL 错误: {e.reason}", file=sys.stderr)
        return False
    except TimeoutError:
        print(f"下载超时: 超过 {timeout} 秒", file=sys.stderr)
        return False
    except Exception as e:
        print(f"下载失败: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="从 URL 下载文件")
    parser.add_argument("url", help="要下载的文件 URL")
    parser.add_argument("-o", "--output", help="输出文件路径（默认自动检测文件名）")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细进度信息")
    parser.add_argument("-f", "--force", action="store_true", help="覆盖已存在的文件")
    parser.add_argument("--timeout", type=int, default=30, help="请求超时时间（秒），默认30秒")
    parser.add_argument("--user-agent", help="自定义 User-Agent")
    
    args = parser.parse_args()
    
    # 确定输出文件路径
    if args.output:
        output_path = args.output
    else:
        filename = get_filename_from_url(args.url)
        output_path = f"/workspace/{filename}"
    
    # 下载文件
    success = download_file(
        url=args.url,
        output_path=output_path,
        verbose=args.verbose,
        force=args.force,
        timeout=args.timeout,
        user_agent=args.user_agent
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()