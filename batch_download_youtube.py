import os
import sys
import time
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError
except ImportError:
    print("正在安装yt-dlp库...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

def download_video(url, output_path='.', proxy=None, format='best', max_retries=3, index=None, total=None):
    """
    使用yt-dlp下载YouTube视频
    
    Args:
        url (str): YouTube视频链接
        output_path (str): 保存路径
        proxy (str): 代理地址，例如 'http://127.0.0.1:2090'
        format (str): 视频格式，默认为最佳质量
        max_retries (int): 最大重试次数
        index (int): 当前下载的索引（用于批量下载）
        total (int): 总下载数量（用于批量下载）
        
    Returns:
        tuple: (成功与否, 视频标题, 错误信息)
    """
    # 确保输出目录存在
    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)
        print(f"创建目录: {output_path}")
    
    # 设置yt-dlp选项
    ydl_opts = {
        'format': format,
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'no_warnings': False,
        'ignoreerrors': True,
        'quiet': False,
        'verbose': False,  # 减少详细输出
        'progress': True,
        'geo_bypass': True,  # 尝试绕过地理限制
        'geo_bypass_country': 'US',
        'socket_timeout': 30,  # 设置套接字超时
        'retries': 10,  # 内部重试次数
    }
    
    # 添加代理设置
    if proxy:
        ydl_opts['proxy'] = proxy
    
    prefix = f"[{index}/{total}] " if index is not None and total is not None else ""
    retries = 0
    error_msg = ""
    
    while retries < max_retries:
        try:
            print(f"{prefix}尝试下载 {url}...")
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    title = info.get('title', '未知标题')
                    print(f"{prefix}下载完成: {title}")
                    return True, title, ""
                else:
                    error_msg = "无法获取视频信息"
                    print(f"{prefix}{error_msg}")
        except DownloadError as e:
            error_msg = f"下载错误: {e}"
            print(f"{prefix}{error_msg}")
        except Exception as e:
            error_msg = f"发生错误: {e}"
            print(f"{prefix}{error_msg}")
        
        retries += 1
        if retries < max_retries:
            wait_time = 2 ** retries
            print(f"{prefix}等待 {wait_time} 秒后重试... ({retries}/{max_retries})")
            time.sleep(wait_time)
    
    print(f"{prefix}达到最大重试次数，下载失败")
    return False, "", error_msg

def read_urls_from_file(file_path):
    """从文件中读取URL列表"""
    urls = []
    
    # 检查文件扩展名
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    try:
        if ext == '.csv':
            # 从CSV文件读取
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        urls.append(row[0].strip())
        else:
            # 从文本文件读取
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        urls.append(line)
    except Exception as e:
        print(f"读取文件时出错: {e}")
    
    return urls

def save_results(results, output_path):
    """保存下载结果到CSV文件"""
    result_file = os.path.join(output_path, "download_results.csv")
    try:
        with open(result_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["URL", "状态", "标题", "错误信息"])
            for url, success, title, error in results:
                writer.writerow([url, "成功" if success else "失败", title, error])
        print(f"下载结果已保存到: {result_file}")
    except Exception as e:
        print(f"保存结果时出错: {e}")

def batch_download(urls, output_path, proxy, format, max_workers=3, max_retries=3):
    """批量下载视频"""
    total = len(urls)
    results = []
    
    print(f"开始批量下载 {total} 个视频...")
    
    # 使用线程池并发下载
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有下载任务
        future_to_url = {
            executor.submit(
                download_video, 
                url, 
                output_path, 
                proxy, 
                format, 
                max_retries,
                i+1, 
                total
            ): url for i, url in enumerate(urls)
        }
        
        # 处理完成的任务
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                success, title, error = future.result()
                results.append((url, success, title, error))
            except Exception as e:
                print(f"处理下载结果时出错: {e}")
                results.append((url, False, "", str(e)))
    
    # 统计结果
    success_count = sum(1 for _, success, _, _ in results if success)
    print(f"\n批量下载完成: 成功 {success_count}/{total}")
    
    # 保存结果
    save_results(results, output_path)
    
    return results

def main():
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='批量下载YouTube视频')
        parser.add_argument('--file', help='包含YouTube视频链接的文件路径（每行一个链接，或CSV文件）')
        parser.add_argument('--urls', nargs='+', help='要下载的YouTube视频链接列表')
        parser.add_argument('--path', default='.', help='保存路径（默认为当前目录）')
        parser.add_argument('--proxy', default='http://127.0.0.1:2090', help='代理地址（默认为http://127.0.0.1:2090）')
        parser.add_argument('--format', default='best', help='视频格式（默认为best）')
        parser.add_argument('--no-proxy', action='store_true', help='不使用代理')
        parser.add_argument('--workers', type=int, default=3, help='同时下载的视频数量（默认为3）')
        parser.add_argument('--retries', type=int, default=3, help='每个视频的最大重试次数（默认为3）')
        args = parser.parse_args()
        
        # 获取URL列表
        urls = []
        if args.file:
            urls = read_urls_from_file(args.file)
            print(f"从文件 {args.file} 中读取了 {len(urls)} 个URL")
        elif args.urls:
            urls = args.urls
            print(f"从命令行参数中读取了 {len(urls)} 个URL")
        else:
            # 交互式输入
            print("请输入YouTube视频链接（每行一个，输入空行结束）:")
            while True:
                line = input().strip()
                if not line:
                    break
                urls.append(line)
        
        if not urls:
            print("没有提供任何URL，退出程序")
            return
        
        # 获取保存路径
        download_path = args.path
        if download_path == '.' and not (args.file or args.urls):
            download_path = input("请输入保存路径（留空为当前目录）: ").strip() or '.'
        
        # 代理设置
        proxy = None if args.no_proxy else args.proxy
        if not (args.file or args.urls) and not args.no_proxy:
            use_proxy = input(f"是否使用代理 {proxy}？(y/n): ").lower().strip() == 'y'
            if not use_proxy:
                proxy = None
            elif use_proxy:
                custom_proxy = input("请输入自定义代理地址（留空使用默认值）: ").strip()
                if custom_proxy:
                    proxy = custom_proxy
        
        # 显示配置信息
        print(f"下载URL数量: {len(urls)}")
        print(f"保存路径: {download_path}")
        print(f"代理设置: {proxy}")
        print(f"视频格式: {args.format}")
        print(f"并发下载数: {args.workers}")
        print(f"最大重试次数: {args.retries}")
        
        # 确认是否继续
        if not (args.file or args.urls):
            confirm = input("是否开始下载？(y/n): ").lower().strip()
            if confirm != 'y':
                print("用户取消下载")
                return
        
        # 开始批量下载
        batch_download(
            urls, 
            download_path, 
            proxy, 
            args.format, 
            args.workers, 
            args.retries
        )
        
    except KeyboardInterrupt:
        print("\n用户取消操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
