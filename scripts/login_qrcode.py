"""
小红书扫码登录脚本

使用方式:
    # 使用默认参数
    python scripts/login_qrcode.py

    # 指定截图保存目录
    python scripts/login_qrcode.py --output D:/screenshots

    # 指定服务地址和端口
    python scripts/login_qrcode.py --host 127.0.0.1 --port 8989

参数说明:
    --output   截图保存目录（默认项目根目录 output/）
    --host     服务地址（默认 127.0.0.1）
    --port     服务端口（默认 8989）

执行流程:
    1. 跳转到创作者中心登录页
    2. 等待 5 秒（页面加载 + 二维码渲染）
    3. 点击二维码图片
    4. 等待 3 秒
    5. 截图当前页面并打印保存路径
"""

import time
import argparse
import requests

DEFAULT_HOST   = "127.0.0.1"
DEFAULT_PORT   = 8989
LOGIN_URL      = "https://creator.xiaohongshu.com/login?source=&redirectReason=401&lastUrl=%252Fpublish%252Fpublish%253Ffrom%253Dmenu%2526target%253Dimage"
SEL_QRCODE     = "img.css-wemwzq"


def api(host: str, port: int, method: str, path: str, **kwargs):
    url = f"http://{host}:{port}/api{path}"
    resp = requests.request(method, url, timeout=30, **kwargs)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success", True):
        raise RuntimeError(f"接口返回失败: {data}")
    return data


def is_logged_in(host: str, port: int) -> bool:
    """检查页面中是否存在「退出登录」元素，存在则代表已登录"""
    result = api(host, port, "POST", "/eval", json={
        "expression": "!!document.querySelector('div.menu-list .popover_text')"
    })
    return result.get("result", False)


def main():
    parser = argparse.ArgumentParser(description="小红书扫码登录脚本")
    parser.add_argument("--output", default=None, help="截图保存目录（默认 output/）")
    parser.add_argument("--host",   default=DEFAULT_HOST, help="服务地址")
    parser.add_argument("--port",   type=int, default=DEFAULT_PORT, help="服务端口")
    args = parser.parse_args()

    base = (args.host, args.port)
    print(f"[*] 目标服务: http://{args.host}:{args.port}")

    # ── 检查服务就绪 ────────────────────────────────────────────────────────
    status = api(*base, "GET", "/status")
    print(f"[+] 服务就绪，当前页面: {status['current_url']}")

    # ── 检查是否已登录 ───────────────────────────────────────────────────────
    if is_logged_in(*base):
        print("[+] 用户已登录，无需登录")
        return

    # ── Step 1：跳转登录页 ───────────────────────────────────────────────────
    print("[*] Step 1 - 跳转登录页 ...")
    result = api(*base, "POST", "/navigate", json={
        "url": LOGIN_URL,
        "wait_until": "domcontentloaded",
    })
    print(f"[+] 已跳转: {result['url']}")

    # ── 等待 5 秒（二维码渲染） ──────────────────────────────────────────────
    print("[*] 等待 5 秒，等待二维码渲染 ...")
    time.sleep(5)

    # ── Step 2：点击二维码 ───────────────────────────────────────────────────
    print(f"[*] Step 2 - 点击二维码: {SEL_QRCODE!r}")
    api(*base, "POST", "/click", json={"selector": SEL_QRCODE})
    print("[+] 二维码已点击，请用手机扫码")

    # ── 等待 3 秒 ────────────────────────────────────────────────────────────
    print("[*] 等待 3 秒 ...")
    time.sleep(3)

    # ── Step 3：截图 ─────────────────────────────────────────────────────────
    print("[*] Step 3 - 截图当前页面 ...")
    result = api(*base, "POST", "/screenshot", json={
        "output_dir": args.output,
        "filename": "login_qrcode.png",
    })
    print(f"[+] 截图已保存: {result['path']}")


if __name__ == "__main__":
    main()
