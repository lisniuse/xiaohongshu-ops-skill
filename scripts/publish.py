"""
小红书图文发布脚本

使用方式:
    # 使用默认参数发布
    python scripts/publish.py

    # 指定图片（多张空格分隔）
    python scripts/publish.py --files D:/img/1.png D:/img/2.png D:/img/3.png

    # 指定标题、正文、话题
    python scripts/publish.py --title "我的标题" --content "正文内容" --topics 美食 旅行 生活

    # 完整参数
    python scripts/publish.py \
        --files D:/img/1.png D:/img/2.png \
        --title "OpenClaw AI 助手" \
        --content "分享一下这个好用的工具" \
        --topics AI工具 效率 科技 \
        --host 127.0.0.1 \
        --port 8989

参数说明:
    --files    图片绝对路径，支持多张（空格分隔，默认项目根目录 image.png）
    --title    笔记标题（默认「测试标题」）
    --content  笔记正文（默认「测试内容」）
    --topics   话题列表，不带 #（空格分隔，默认 话题A B C D）
    --host     服务地址（默认 127.0.0.1）
    --port     服务端口（默认 8989）

执行流程:
    1. 跳转图文发布页
    2. 上传图片
    3. 输入标题
    4. 输入正文
    5. 输入话题（每个话题换行后 # 开头，回车确认）
    6. 开启原创声明
    7. 弹窗勾选协议
    8. 点击「声明原创」
    9. 点击「发布」
"""

import time
import argparse
from pathlib import Path
import requests

DEFAULT_HOST  = "127.0.0.1"
DEFAULT_PORT  = 8989

PUBLISH_URL    = "https://creator.xiaohongshu.com/publish/publish?from=menu&target=image"
SEL_FILE_INPUT = "input[type='file']"
SEL_TITLE      = "input.d-text[placeholder='填写标题会有更多赞哦']"
SEL_CONTENT    = ".tiptap.ProseMirror[contenteditable='true']"
SEL_ORIGINAL        = ".custom-switch-card:has(.has-tips) .d-switch-simulator.unchecked"
SEL_ORIGINAL_AGREE  = ".d-checkbox.bg-red .d-checkbox-simulator"
SEL_ORIGINAL_SUBMIT = "button.custom-button.bg-red:has-text('声明原创')"
SEL_PUBLISH         = "button.custom-button.bg-red:has-text('发布')"

DEFAULT_TITLE   = "测试标题"
DEFAULT_CONTENT = "测试内容"
DEFAULT_TOPICS  = ["话题A", "话题B", "话题C", "话题D"]

# 默认图片：项目根目录下的 image.png
DEFAULT_FILES = [str(Path(__file__).parent.parent / "image.png")]


def api(host: str, port: int, method: str, path: str, **kwargs):
    url = f"http://{host}:{port}/api{path}"
    resp = requests.request(method, url, timeout=30, **kwargs)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success", True):
        raise RuntimeError(f"接口返回失败: {data}")
    return data


def press(host, port, key: str, count: int = 1):
    return api(host, port, "POST", "/key", json={"key": key, "count": count})


def main():
    parser = argparse.ArgumentParser(description="小红书图文发布脚本")
    parser.add_argument("--files", nargs="+", default=DEFAULT_FILES,
                        help="要上传的图片绝对路径（可多张，空格分隔）")
    parser.add_argument("--title",   default=DEFAULT_TITLE,   help="笔记标题")
    parser.add_argument("--content", default=DEFAULT_CONTENT, help="笔记正文")
    parser.add_argument("--topics",  nargs="+", default=DEFAULT_TOPICS,
                        help="话题列表（空格分隔，不带 #）")
    parser.add_argument("--host", default=DEFAULT_HOST, help="服务地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="服务端口")
    args = parser.parse_args()

    base = (args.host, args.port)
    print(f"[*] 目标服务: http://{args.host}:{args.port}")
    print(f"[*] 上传图片: {args.files}")
    print(f"[*] 标题: {args.title}")
    print(f"[*] 正文: {args.content}")
    print(f"[*] 话题: {args.topics}")

    # ── 检查服务就绪 ────────────────────────────────────────────────────────
    status = api(*base, "GET", "/status")
    print(f"[+] 服务就绪，当前页面: {status['current_url']}")

    # ── Step 1：跳转发布页 ───────────────────────────────────────────────────
    print(f"[*] Step 1 - 跳转到图文发布页 ...")
    result = api(*base, "POST", "/navigate", json={
        "url": PUBLISH_URL,
        "wait_until": "domcontentloaded",
    })
    print(f"[+] 已跳转: {result['url']}")

    time.sleep(2)

    # ── Step 2：上传图片 ─────────────────────────────────────────────────────
    print(f"[*] Step 2 - 上传 {len(args.files)} 张图片 ...")
    api(*base, "POST", "/upload_file", json={
        "selector": SEL_FILE_INPUT,
        "files": args.files,
    })
    print(f"[+] 图片上传完成")

    time.sleep(2)

    # ── Step 3：输入标题 ─────────────────────────────────────────────────────
    print(f"[*] Step 3 - 输入标题: {args.title!r}")
    api(*base, "POST", "/click",  json={"selector": SEL_TITLE})
    api(*base, "POST", "/type",   json={"selector": SEL_TITLE, "text": args.title})
    print("[+] 标题输入完成")

    time.sleep(1)

    # ── Step 4：输入正文 ─────────────────────────────────────────────────────
    print(f"[*] Step 4 - 输入正文: {args.content!r}")
    api(*base, "POST", "/type", json={"selector": SEL_CONTENT, "text": args.content})
    print("[+] 正文输入完成")

    time.sleep(0.5)

    # ── Step 5：输入话题（回车 → #话题名 → 回车） ────────────────────────────
    print(f"[*] Step 5 - 输入 {len(args.topics)} 个话题 ...")
    press(*base, "Enter")
    for topic in args.topics:
        time.sleep(1)
        api(*base, "POST", "/type", json={
            "selector": SEL_CONTENT,
            "text": f"#{topic}",
            "delay": 60,
            "append": True,
        })
        time.sleep(1)
        press(*base, "Enter")
        time.sleep(1)
        print(f"[+]   #{topic} ✓")

    print("[+] 所有话题输入完成")

    time.sleep(0.5)

    # ── Step 6：点击原创声明开关 ─────────────────────────────────────────────
    print(f"[*] Step 6 - 点击原创声明 ...")
    api(*base, "POST", "/click", json={"selector": SEL_ORIGINAL})
    print("[+] 原创声明已开启")

    time.sleep(1)

    # ── Step 7：弹窗 - 勾选「我已阅读并同意」 ────────────────────────────────
    print(f"[*] Step 7 - 勾选原创声明协议 ...")
    api(*base, "POST", "/click", json={"selector": SEL_ORIGINAL_AGREE})
    print("[+] 协议已勾选")

    time.sleep(1)

    # ── Step 8：弹窗 - 点击「声明原创」按钮 ──────────────────────────────────
    print(f"[*] Step 8 - 点击「声明原创」按钮 ...")
    api(*base, "POST", "/click", json={"selector": SEL_ORIGINAL_SUBMIT})
    print("[+] 原创声明完成")

    time.sleep(1)

    # ── Step 9：点击发布按钮 ──────────────────────────────────────────────────
    print(f"[*] Step 9 - 点击「发布」按钮 ...")
    api(*base, "POST", "/click", json={"selector": SEL_PUBLISH})
    print("[+] 发布成功！")


if __name__ == "__main__":
    main()
