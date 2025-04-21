import os
import sys
import time
import argparse

try:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError
except ImportError:
    print("正在安装yt-dlp库...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

def download_video(url, output_path='.', proxy=None, format='best', max_retries=3):
    """
    使用yt-dlp下载YouTube视频

    Args:
        url (str): YouTube视频链接
        output_path (str): 保存路径
        proxy (str): 代理地址，例如 'http://127.0.0.1:2090'
        format (str): 视频格式，默认为最佳质量
        max_retries (int): 最大重试次数

    Returns:
        bool: 下载成功返回True，失败返回False
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

    retries = 0
    while retries < max_retries:
        try:
            print(f"尝试下载 {url}...")
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    print(f"下载完成: {info.get('title', '未知标题')}")
                    return True
                else:
                    print("无法获取视频信息")
        except DownloadError as e:
            print(f"下载错误: {e}")
        except Exception as e:
            print(f"发生错误: {e}")

        retries += 1
        if retries < max_retries:
            wait_time = 2 ** retries
            print(f"等待 {wait_time} 秒后重试... ({retries}/{max_retries})")
            time.sleep(wait_time)

    print("达到最大重试次数，下载失败")
    return False

def list_formats(url, proxy=None):
    """列出可用的视频格式"""
    ydl_opts = {
        'listformats': True,
        'quiet': True,
        'no_warnings': True,
    }
    if proxy:
        ydl_opts['proxy'] = proxy

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                print("无法获取视频信息")
                return []

            formats = info.get('formats', [])
            if not formats:
                print("没有可用的格式")
                return []

            print("\n可用的视频格式:")
            print("-" * 80)
            print(f"{'格式ID':<10}{'扩展名':<10}{'分辨率':<15}{'文件大小':<15}{'备注':<20}")
            print("-" * 80)

            for f in formats:
                format_id = f.get('format_id', 'N/A')
                ext = f.get('ext', 'N/A')
                resolution = f.get('resolution', 'N/A')
                filesize = f.get('filesize', 0)
                if filesize:
                    filesize = f"{filesize / 1024 / 1024:.2f} MB"
                else:
                    filesize = "未知"
                note = f.get('format_note', '')

                print(f"{format_id:<10}{ext:<10}{resolution:<15}{filesize:<15}{note:<20}")

            print("-" * 80)
            print("特殊格式选项:")
            print("best       - 最佳视频和音频质量")
            print("bestvideo+bestaudio - 分别选择最佳视频和音频并合并")
            print("-" * 80)

            return formats
    except Exception as e:
        print(f"获取格式列表时出错: {e}")
        return []

def main():
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='使用yt-dlp下载YouTube视频')
        parser.add_argument('--url', help='YouTube视频链接')
        parser.add_argument('--path', default='.', help='保存路径（默认为当前目录）')
        parser.add_argument('--proxy', default='http://127.0.0.1:10809', help='代理地址（默认为http://127.0.0.1:2090）')
        parser.add_argument('--format', default='best', help='视频格式（默认为best）')
        parser.add_argument('--no-proxy', action='store_true', help='不使用代理')
        parser.add_argument('--list-formats', action='store_true', help='列出可用的视频格式')
        args = parser.parse_args()

        # 如果没有提供URL，则从输入获取
        video_url = args.url
        if not video_url:
            video_url = input("请输入YouTube视频链接: ")

        # 如果没有提供路径，则从输入获取
        download_path = args.path
        if download_path == '.' and not args.url:  # 只有在交互模式下才询问
            download_path = input("请输入保存路径（留空为当前目录）: ").strip() or '.'

        # 代理设置
        proxy = None if args.no_proxy else args.proxy

        # 如果是交互模式，询问是否使用代理
        if not args.url and not args.no_proxy:
            use_proxy = input(f"是否使用代理 {proxy}？(y/n): ").lower().strip() == 'y'
            if not use_proxy:
                proxy = None
            elif use_proxy:
                custom_proxy = input("请输入自定义代理地址（留空使用默认值）: ").strip()
                if custom_proxy:
                    proxy = custom_proxy

        print(f"视频链接: {video_url}")
        print(f"保存路径: {download_path}")
        print(f"代理设置: {proxy}")

        # 如果需要列出格式
        video_format = args.format
        if args.list_formats or (not args.url and input("是否列出可用的视频格式？(y/n): ").lower().strip() == 'y'):
            formats = list_formats(video_url, proxy)
            if formats and not args.format:
                format_choice = input("请选择格式ID（直接回车使用best）: ").strip()
                if format_choice:
                    video_format = format_choice

        print(f"视频格式: {video_format}")

        # 下载视频
        success = download_video(video_url, download_path, proxy, video_format)

        # 如果使用代理失败，询问是否尝试直接下载
        if not success and proxy:
            try_direct = input("使用代理下载失败，是否尝试直接下载？(y/n): ").lower().strip() == 'y'
            if try_direct:
                print("尝试直接下载...")
                download_video(video_url, download_path, None, args.format)

    except KeyboardInterrupt:
        print("\n用户取消操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
