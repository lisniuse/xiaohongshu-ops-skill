"""
小红书手机号登录 - 自动填写手机号并获取验证码

使用方式:
    # 使用默认手机号
    python scripts/login_phone.py

    # 指定手机号
    python scripts/login_phone.py --phone 18676719432

    # 指定服务地址和端口
    python scripts/login_phone.py --phone 18676719432 --host 127.0.0.1 --port 8989

参数说明:
    --phone    手机号码（默认 18676719432）
    --host     服务地址（默认 127.0.0.1）
    --port     服务端口（默认 8989）

执行流程:
    1. 刷新页面
    2. 点击手机号输入框并输入手机号
    3. 勾选同意协议
    4. 点击「获取验证码」
"""

import time
import argparse
import requests

# ── 默认配置 ────────────────────────────────────────────────────────────────
DEFAULT_PHONE = "18676719432"
DEFAULT_HOST  = "127.0.0.1"
DEFAULT_PORT  = 8989

# 选择器
SEL_PHONE_INPUT  = 'input[placeholder="输入手机号"]'
SEL_AGREE_ICON   = "span.agree-icon"
SEL_CODE_BUTTON  = "span.code-button"


def api(host: str, port: int, method: str, path: str, **kwargs):
    url = f"http://{host}:{port}/api{path}"
    resp = requests.request(method, url, timeout=15, **kwargs)
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
    parser = argparse.ArgumentParser(description="小红书手机号登录脚本")
    parser.add_argument("--phone", default=DEFAULT_PHONE, help="手机号码")
    parser.add_argument("--host",  default=DEFAULT_HOST,  help="服务地址")
    parser.add_argument("--port",  type=int, default=DEFAULT_PORT, help="服务端口")
    args = parser.parse_args()

    base = (args.host, args.port)
    print(f"[*] 目标服务: http://{args.host}:{args.port}")

    # ── 检查服务是否就绪 ────────────────────────────────────────────────────
    status = api(*base, "GET", "/status")
    print(f"[+] 服务就绪，当前页面: {status['current_url']}")

    # ── 检查是否已登录 ───────────────────────────────────────────────────────
    if is_logged_in(*base):
        print("[+] 用户已登录，无需登录")
        return

    # ── 刷新页面 ────────────────────────────────────────────────────────────
    print("[*] 刷新页面 ...")
    api(*base, "POST", "/reload")
    print("[+] 页面刷新完成")

    # ── Step 1：点击手机号输入框 ────────────────────────────────────────────
    print(f"[*] Step 1 - 点击手机号输入框: {SEL_PHONE_INPUT!r}")
    api(*base, "POST", "/click", json={"selector": SEL_PHONE_INPUT})
    print("[+] 点击成功")

    # ── Step 1：输入手机号 ──────────────────────────────────────────────────
    print(f"[*] Step 1 - 输入手机号: {args.phone}")
    api(*base, "POST", "/type", json={
        "selector": SEL_PHONE_INPUT,
        "text": args.phone,
        "delay": 80,
    })
    print("[+] 手机号输入完成")

    # ── 等待 2000ms ─────────────────────────────────────────────────────────
    print("[*] 等待 2000ms ...")
    time.sleep(1)

    # ── Step 2：勾选同意协议 ────────────────────────────────────────────────
    print(f"[*] Step 2 - 点击同意协议: {SEL_AGREE_ICON!r}")
    api(*base, "POST", "/click", json={"selector": SEL_AGREE_ICON})
    print("[+] 已勾选同意协议")

    time.sleep(1)

    # ── Step 3：点击「获取验证码」 ──────────────────────────────────────────
    print(f"[*] Step 3 - 点击获取验证码按钮: {SEL_CODE_BUTTON!r}")
    api(*base, "POST", "/click", json={"selector": SEL_CODE_BUTTON})
    print("[+] 已点击「获取验证码」，请查收短信")

if __name__ == "__main__":
    main()
