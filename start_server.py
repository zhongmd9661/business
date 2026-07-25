"""招待费智能审核系统 - 局域网启动脚本
用法: python start_server.py [--port 8000] [--host 0.0.0.0]
默认监听所有网卡 (0.0.0.0)，局域网内其他机器可通过 http://<本机IP>:<端口> 访问
"""
import subprocess
import sys
import socket
import argparse


def get_lan_ip():
    """获取本机局域网 IP 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description="启动招待费智能审核系统")
    parser.add_argument("--port", type=int, default=8099, help="服务端口 (默认 8099)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址 (默认 0.0.0.0)")
    args = parser.parse_args()

    lan_ip = get_lan_ip()

    print("=" * 60)
    print("  招待费智能审核系统")
    print("=" * 60)
    print(f"  本机访问: http://127.0.0.1:{args.port}")
    print(f"  局域网访问: http://{lan_ip}:{args.port}")
    print("=" * 60)
    print("  按 Ctrl+C 停止服务")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.web_service.app:app",
        "--host", args.host,
        "--port", str(args.port),
        "--reload",  # 开发模式热重载
    ]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n服务已停止。")


if __name__ == "__main__":
    main()
