"""
小红书 Playwright HTTP 控制服务

启动后通过 HTTP API 控制浏览器操作小红书。

依赖安装:
    pip install fastapi uvicorn playwright
    playwright install chromium

启动:
    python xhs_server.py

API 示例:
    POST http://localhost:8989/api/screenshot
    POST http://localhost:8989/api/navigate
    POST http://localhost:8989/api/click
    GET  http://localhost:8989/api/status
"""

import sys
import re
import argparse
import tempfile
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


# ── 全局状态 ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "output"

playwright_instance = None
browser: Browser | None = None
context: BrowserContext | None = None
page: Page | None = None
HEADLESS: bool = False          # 由命令行参数控制，入口处赋值
USER_DATA_DIR: Path | None = None   # 由命令行参数控制，入口处赋值
_TEMP_SESSION_DIR: Path | None = None   # 临时 session 目录，退出时清理


# ── 反检测：注入到每个新页面的 JS ────────────────────────────────────────────
STEALTH_JS = """
() => {
    // 1. 删除 webdriver 标记
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // 2. 修复 plugins / mimeTypes（无头浏览器通常为空）
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const arr = [
                { name: 'Chrome PDF Plugin',    filename: 'internal-pdf-viewer',  description: 'Portable Document Format' },
                { name: 'Chrome PDF Viewer',    filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                { name: 'Native Client',        filename: 'internal-nacl-plugin',  description: '' },
            ];
            arr.item   = i => arr[i];
            arr.namedItem = n => arr.find(p => p.name === n) || null;
            arr.refresh = () => {};
            Object.setPrototypeOf(arr, PluginArray.prototype);
            return arr;
        }
    });

    // 3. 语言列表
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });

    // 4. 硬件并发数（与真实机器一致）
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });

    // 5. 设备内存
    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

    // 6. 屏蔽 __playwright / __pw_* 等全局变量
    const _toHide = ['__playwright', '__pw_manual', '__PW_inspect', 'calledPlaywright'];
    _toHide.forEach(k => { try { delete window[k]; } catch(_) {} });

    // 7. chrome runtime 对象（无头模式下可能缺失）
    if (!window.chrome) {
        window.chrome = {
            app: { isInstalled: false, InstallState: {}, RunningState: {} },
            runtime: {
                PlatformOs: {}, PlatformArch: {}, PlatformNaclArch: {},
                RequestUpdateCheckStatus: {}, OnInstalledReason: {},
                OnRestartRequiredReason: {},
                connect: () => {},
                sendMessage: () => {},
            },
        };
    }

    // 8. Notification.permission 返回 'default' 而非 'denied'
    try {
        Object.defineProperty(Notification, 'permission', { get: () => 'default' });
    } catch(_) {}

    // 9. WebGL 厂商 / 渲染器伪装
    const getParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        if (param === 37445) return 'Intel Inc.';
        if (param === 37446) return 'Intel Iris OpenGL Engine';
        return getParam.call(this, param);
    };
    const getParam2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(param) {
        if (param === 37445) return 'Intel Inc.';
        if (param === 37446) return 'Intel Iris OpenGL Engine';
        return getParam2.call(this, param);
    };

    // 10. 鼠标移动轨迹痕迹（让页面认为鼠标存在）
    window.addEventListener('mousemove', () => {}, { passive: true });
}
"""


# ── 启动 / 关闭 ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global playwright_instance, browser, context, page, _TEMP_SESSION_DIR

    print("[*] 启动 Playwright 浏览器 ...")
    print(f"[*] 用户数据目录: {USER_DATA_DIR}")
    playwright_instance = await async_playwright().start()
    # launch_persistent_context 直接返回 BrowserContext（含持久化 session）
    context = await playwright_instance.chromium.launch_persistent_context(
        user_data_dir=str(USER_DATA_DIR),
        headless=HEADLESS,
        viewport={"width": 1440, "height": 900},
        screen={"width": 1440, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        permissions=["geolocation", "notifications"],
        color_scheme="light",
        extra_http_headers={
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--window-size=1440,900",
            "--start-maximized",
            "--disable-extensions",
            "--disable-plugins-discovery",
            "--no-first-run",
            "--no-default-browser-check",
        ],
        ignore_default_args=["--enable-automation"],
    )

    # 每个新页面创建时自动注入反检测脚本（在任何页面 JS 执行前）
    await context.add_init_script(STEALTH_JS)

    page = await context.new_page()

    # 拦截并过滤暴露自动化身份的请求头
    async def remove_automation_headers(route, request):
        headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in ("x-requested-with",)}
        await route.continue_(headers=headers)

    await page.route("**/*", remove_automation_headers)

    await page.goto("https://www.xiaohongshu.com/", wait_until="domcontentloaded")
    print("[+] 小红书已打开，HTTP 服务就绪")

    yield

    print("[*] 关闭浏览器 ...")
    await context.close()
    await playwright_instance.stop()

    # 临时 session 退出时自动清理
    if _TEMP_SESSION_DIR and _TEMP_SESSION_DIR.exists():
        shutil.rmtree(_TEMP_SESSION_DIR, ignore_errors=True)
        print(f"[*] 临时 session 已清理: {_TEMP_SESSION_DIR}")


app = FastAPI(
    title="小红书 Playwright 控制器",
    description="通过 HTTP API 控制 Playwright 浏览器操作小红书",
    version="1.0.0",
    lifespan=lifespan,
)

# 所有业务接口挂载到 /api 前缀
router = APIRouter(prefix="/api")


# ── 工具函数 ────────────────────────────────────────────────────────────────
def resolve_output_dir(folder: str | None) -> Path:
    d = Path(folder) if folder else DEFAULT_OUTPUT_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_page():
    if page is None:
        raise HTTPException(status_code=503, detail="浏览器未就绪")
    if page.is_closed():
        raise HTTPException(status_code=503, detail="页面已关闭，请重启服务")


# ── Pydantic 请求体 ──────────────────────────────────────────────────────────
class ScreenshotRequest(BaseModel):
    output_dir: str | None = None       # 留空 → output/
    filename: str | None = None         # 留空 → screenshot_<timestamp>.png
    full_page: bool = False


class NavigateRequest(BaseModel):
    url: str
    wait_until: str = "domcontentloaded"  # load | domcontentloaded | networkidle


class ClickRequest(BaseModel):
    selector: str
    timeout: int = 5000
    offset_x: int | None = None   # 相对元素中心的 X 偏移（像素），负值向左
    offset_y: int | None = None   # 相对元素中心的 Y 偏移（像素），负值向上


class TypeRequest(BaseModel):
    selector: str
    text: str
    delay: int = 50
    append: bool = False   # True = 追加输入，不清空已有内容


class ScrollRequest(BaseModel):
    direction: str = "down"              # down | up
    distance: int = 600


class EvalRequest(BaseModel):
    expression: str


# ── API 端点（均在 /api 下） ─────────────────────────────────────────────────

@router.get("/status", summary="检查服务与浏览器状态")
async def status():
    ensure_page()
    return {
        "status": "ok",
        "current_url": page.url,
        "title": await page.title(),
    }


@router.post("/screenshot", summary="截图当前页面")
async def screenshot(req: ScreenshotRequest = ScreenshotRequest()):
    """
    截图当前页面并保存到指定目录。

    - **output_dir**: 保存目录（留空 → 脚本同级 `output/` 目录）
    - **filename**: 文件名（留空 → `screenshot_<时间戳>.png`）
    - **full_page**: 是否截取整页（默认仅截可见区域）
    """
    ensure_page()
    out_dir = resolve_output_dir(req.output_dir)
    fname = req.filename or f"screenshot_{ts()}.png"
    if not fname.endswith(".png"):
        fname += ".png"
    save_path = out_dir / fname

    await page.screenshot(path=str(save_path), full_page=req.full_page)
    return {
        "success": True,
        "path": str(save_path),
        "url": page.url,
    }


@router.get("/screenshot/download", summary="截图并直接返回图片文件")
async def screenshot_download(full_page: bool = False):
    ensure_page()
    out_dir = resolve_output_dir(None)
    save_path = out_dir / f"screenshot_{ts()}.png"
    await page.screenshot(path=str(save_path), full_page=full_page)
    return FileResponse(save_path, media_type="image/png", filename=save_path.name)


@router.post("/navigate", summary="跳转到指定 URL")
async def navigate(req: NavigateRequest):
    ensure_page()
    resp = await page.goto(req.url, wait_until=req.wait_until)
    return {
        "success": True,
        "url": page.url,
        "title": await page.title(),
        "status": resp.status if resp else None,
    }


@router.post("/click", summary="点击页面元素")
async def click(req: ClickRequest):
    """
    点击指定元素。可通过 `offset_x` / `offset_y` 指定相对于元素**中心**的偏移量。

    示例：元素 A 中心向上 200px 处 → `{"selector": "#A", "offset_y": -200}`
    """
    ensure_page()
    try:
        kwargs = {"timeout": req.timeout}
        if req.offset_x is not None or req.offset_y is not None:
            # 先获取元素的 bounding box，计算目标绝对坐标后用 page.mouse.click
            box = await page.locator(req.selector).bounding_box(timeout=req.timeout)
            if box is None:
                raise HTTPException(status_code=400, detail="元素不可见，无法获取位置")
            center_x = box["x"] + box["width"] / 2
            center_y = box["y"] + box["height"] / 2
            target_x = center_x + (req.offset_x or 0)
            target_y = center_y + (req.offset_y or 0)
            await page.mouse.click(target_x, target_y)
        else:
            await page.click(req.selector, **kwargs)
        return {"success": True, "selector": req.selector, "url": page.url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/type", summary="在输入框中输入文字")
async def type_text(req: TypeRequest):
    """
    兼容普通 input/textarea 和 contenteditable 富文本编辑器。
    - 普通输入框：先 fill 清空再 type
    - contenteditable（如 ProseMirror/tiptap）：click 聚焦后直接 keyboard.type
    """
    ensure_page()
    try:
        locator = page.locator(req.selector)
        tag = await locator.evaluate("el => el.tagName.toLowerCase()")
        is_contenteditable = await locator.evaluate(
            "el => el.isContentEditable || el.getAttribute('contenteditable') === 'true'"
        )
        if is_contenteditable:
            await locator.click()
            if not req.append:
                await page.keyboard.press("Control+a")
                await page.keyboard.press("Delete")
            # 将光标移到末尾后输入
            await page.keyboard.press("End")
            await page.keyboard.type(req.text, delay=req.delay)
        else:
            if not req.append:
                await page.fill(req.selector, "")
            await page.type(req.selector, req.text, delay=req.delay)
        return {"success": True, "selector": req.selector, "text": req.text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scroll", summary="滚动页面")
async def scroll(req: ScrollRequest):
    ensure_page()
    dy = req.distance if req.direction == "down" else -req.distance
    await page.evaluate(f"window.scrollBy(0, {dy})")
    return {"success": True, "direction": req.direction, "distance": req.distance}


@router.post("/eval", summary="执行任意 JavaScript")
async def evaluate(req: EvalRequest):
    ensure_page()
    try:
        result = await page.evaluate(req.expression)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/content", summary="获取页面 HTML 内容")
async def get_content():
    ensure_page()
    html = await page.content()
    return JSONResponse({"success": True, "length": len(html), "html": html[:5000]})


@router.post("/reload", summary="刷新当前页面")
async def reload():
    ensure_page()
    await page.reload(wait_until="domcontentloaded")
    return {"success": True, "url": page.url, "title": await page.title()}


class UploadFileRequest(BaseModel):
    selector: str                  # 文件 input 的 CSS 选择器
    files: list[str]               # 本地文件绝对路径列表
    timeout: int = 10000


@router.post("/upload_file", summary="向 input[type=file] 上传本地文件")
async def upload_file(req: UploadFileRequest):
    """
    通过 Playwright set_input_files 向指定 file input 注入本地文件，
    无需打开系统文件选择框。

    - **selector**: CSS 选择器，指向 `<input type="file">`
    - **files**: 本地文件绝对路径列表
    """
    ensure_page()
    missing = [f for f in req.files if not Path(f).exists()]
    if missing:
        raise HTTPException(status_code=400, detail=f"文件不存在: {missing}")
    try:
        await page.locator(req.selector).set_input_files(req.files, timeout=req.timeout)
        return {"success": True, "files": req.files}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class KeyPressRequest(BaseModel):
    key: str                       # Playwright 键名，如 Enter、Tab、Escape、Control+a 等
    count: int = 1                 # 按几次


@router.post("/key", summary="模拟键盘按键")
async def key_press(req: KeyPressRequest):
    """
    按下指定键，支持组合键（如 `Control+a`）和连按（count > 1）。

    常用键名: `Enter` `Tab` `Escape` `Backspace` `ArrowDown` `Control+a`
    """
    ensure_page()
    try:
        for _ in range(req.count):
            await page.keyboard.press(req.key)
        return {"success": True, "key": req.key, "count": req.count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/elements", summary="获取页面所有可见文案元素及选择器")
async def get_elements():
    """
    扫描当前页面所有可见的文案节点，返回每个节点的文本内容与可用 CSS 选择器。

    适用场景：AI 找不到目标元素时调用此接口，获取全量文案地图后重新定位。

    返回字段：
    - **text**: 元素可见文本
    - **tag**: HTML 标签名
    - **selector**: 可直接传入 /click 或 /type 的 CSS 选择器
    - **type**: 元素类型（text / input / button / link / other）
    """
    ensure_page()
    elements = await page.evaluate("""
    () => {
        const getSelector = (el) => {
            // 优先用 id
            if (el.id) return '#' + CSS.escape(el.id);

            // 其次用有意义的 class 组合（过滤动态 hash class）
            const classes = [...el.classList]
                .filter(c => !/^[a-z0-9]{6,}$/.test(c) && !/^--/.test(c) && c.length < 40)
                .slice(0, 3);

            let base = el.tagName.toLowerCase();
            if (classes.length) base += '.' + classes.join('.');

            // 加 placeholder 区分同类 input
            if (el.placeholder) {
                base += `[placeholder="${el.placeholder.replace(/"/g, '\\"')}"]`;
            }

            // 加 name 区分同类 input
            if (el.name && el.tagName !== 'META') {
                base += `[name="${el.name}"]`;
            }

            // 如果选择器匹配多个元素，加 nth-of-type 收窄
            try {
                const matches = document.querySelectorAll(base);
                if (matches.length > 1) {
                    const idx = [...matches].indexOf(el);
                    if (idx > 0) base += `:nth-of-type(${idx + 1})`;
                }
            } catch(_) {}

            return base;
        };

        const classify = (el) => {
            const tag = el.tagName.toLowerCase();
            if (['input', 'textarea'].includes(tag)) return 'input';
            if (tag === 'button') return 'button';
            if (tag === 'a') return 'link';
            if (el.isContentEditable) return 'input';
            return 'text';
        };

        const isVisible = (el) => {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return false;
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
            return rect.top < window.innerHeight && rect.bottom > 0;
        };

        const results = [];
        const seen = new Set();

        const tags = 'button,a,input,textarea,span,div,p,h1,h2,h3,h4,label,[contenteditable]';
        document.querySelectorAll(tags).forEach(el => {
            if (!isVisible(el)) return;

            // 只取叶子节点或 input 类型的文本
            const type = classify(el);
            let text = '';
            if (type === 'input') {
                text = el.value || el.placeholder || el.getAttribute('aria-label') || '';
            } else {
                // 只在没有子元素文本节点时取自身文本（避免重复）
                const directText = [...el.childNodes]
                    .filter(n => n.nodeType === Node.TEXT_NODE)
                    .map(n => n.textContent.trim())
                    .join(' ')
                    .trim();
                text = directText || el.getAttribute('aria-label') || el.getAttribute('title') || '';
            }

            text = text.replace(/\\s+/g, ' ').trim();
            if (!text || text.length < 1 || text.length > 200) return;
            if (seen.has(text + el.tagName)) return;
            seen.add(text + el.tagName);

            results.push({
                text,
                tag: el.tagName.toLowerCase(),
                selector: getSelector(el),
                type,
            });
        });

        return results;
    }
    """)
    return {"success": True, "url": page.url, "count": len(elements), "elements": elements}


# 注册路由
app.include_router(router)


# ── 入口 ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="小红书 Playwright HTTP 控制服务")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP 监听地址（默认 0.0.0.0）")
    parser.add_argument("--port", type=int, default=8989, help="HTTP 监听端口（默认 8989）")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--headless", action="store_true", help="无头模式运行浏览器")
    mode_group.add_argument("--headed",   action="store_true", help="有头模式运行浏览器（默认）")
    parser.add_argument(
        "--user",
        default=None,
        help="用户名（仅字母/数字/下划线）。"
             "指定后在 sessions/<user>/ 下持久化保存；"
             "不指定则在 sessions/ 下创建临时目录，退出时自动清理。",
    )
    args = parser.parse_args()

    # ── 校验用户名 ──────────────────────────────────────────────────────────
    SESSIONS_DIR = SCRIPT_DIR / "sessions"
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    if args.user is not None:
        if not re.fullmatch(r"[A-Za-z0-9_]+", args.user):
            parser.error("--user 只能包含字母、数字和下划线")
        USER_DATA_DIR = SESSIONS_DIR / args.user
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[*] 用户模式: {args.user}  →  {USER_DATA_DIR}")
    else:
        _TEMP_SESSION_DIR = Path(tempfile.mkdtemp(prefix="tmp_", dir=SESSIONS_DIR))
        USER_DATA_DIR = _TEMP_SESSION_DIR
        print(f"[*] 临时会话模式  →  {USER_DATA_DIR}")

    HEADLESS = args.headless

    display_host = "localhost" if args.host in ("0.0.0.0", "::") else args.host
    print(f"[*] 浏览器模式: {'无头' if HEADLESS else '有头'}")
    print(f"[*] HTTP 服务监听 http://{display_host}:{args.port}")
    print(f"[*] 接口文档: http://{display_host}:{args.port}/docs")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
