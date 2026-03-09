# XHS Playwright Server — 环境搭建与接口速查

本技能的浏览器自动化层由一个独立的 **Python HTTP 服务**（`xhs_server.py`）承载。
AI 通过调用 HTTP 接口控制浏览器，不再直接操作 CDP / OpenClaw profile。

---

## 1. 安装依赖

```bash
pip install fastapi uvicorn playwright requests
playwright install chromium
```

---

## 2. 启动服务（强烈推荐使用 PM2 持久运行）

### 推荐：PM2 管理（持久后台运行，崩溃自动重启）

```bash
# 安装 PM2（如未安装）
npm install -g pm2

# 启动服务（持久化用户 alice，有头模式）
pm2 start xhs_server.py --interpreter python --name xhs-server -- --user alice

# 启动无头模式
pm2 start xhs_server.py --interpreter python --name xhs-server -- --user alice --headless

# 查看状态
pm2 status

# 查看日志
pm2 logs xhs-server

# 停止 / 重启
pm2 stop xhs-server
pm2 restart xhs-server

# 开机自启
pm2 save
pm2 startup
```

### 手动启动（临时调试）

```bash
# 有头模式，持久化用户
python xhs_server.py --user alice

# 无头模式
python xhs_server.py --user alice --headless

# 自定义端口
python xhs_server.py --user alice --port 8989
```

---

## 3. 启动参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--user` | 用户名（字母/数字/下划线），session 保存在 `sessions/<user>/`，重启后保留 Cookie / 登录态 | 临时会话，退出自动清理 |
| `--headless` | 无头模式 | 有头模式 |
| `--headed` | 强制有头模式 | — |
| `--host` | 监听地址 | `0.0.0.0` |
| `--port` | 监听端口 | `8989` |

> **最佳实践**：正式运营时固定 `--user <名字>` + PM2，保证登录 Cookie 持久存在，无需反复扫码。

---

## 4. HTTP 接口速查

服务启动后，完整交互文档见：**http://localhost:8989/docs**

所有接口统一前缀 `/api`。

### 状态与导航

```bash
# 检查服务状态 + 当前页面
GET /api/status

# 跳转 URL
POST /api/navigate
{"url": "https://creator.xiaohongshu.com/...", "wait_until": "domcontentloaded"}

# 刷新页面
POST /api/reload
```

### 交互

```bash
# 点击元素（支持偏移量）
POST /api/click
{"selector": "span.code-button"}
{"selector": "#banner", "offset_y": -200}   # 元素中心向上 200px

# 输入文字（自动兼容 contenteditable 富文本编辑器）
POST /api/type
{"selector": "input.d-text", "text": "我的标题"}
{"selector": ".ProseMirror", "text": "正文内容", "append": true}  # 追加不清空

# 模拟键盘按键（支持组合键 / 连按）
POST /api/key
{"key": "Enter"}
{"key": "Control+a"}
{"key": "Enter", "count": 3}

# 滚动页面
POST /api/scroll
{"direction": "down", "distance": 600}
```

### 文件与截图

```bash
# 向 input[type=file] 注入本地文件（不弹文件选择框）
POST /api/upload_file
{"selector": "input[type='file']", "files": ["/path/to/img.png"]}

# 截图保存到文件
POST /api/screenshot
{"output_dir": "/tmp/shots", "filename": "page.png", "full_page": false}

# 截图直接返回图片
GET /api/screenshot/download
```

### JavaScript 执行

```bash
# 执行任意 JS，返回结果
POST /api/eval
{"expression": "document.title"}
{"expression": "!!document.querySelector('div.menu-list .popover_text')"}  # 检测登录态
```

### 页面文案地图（迷路时使用）

```bash
# 扫描当前页面所有可见文案元素，返回文本 + 可用选择器
GET /api/elements
```

返回示例：
```json
{
  "count": 42,
  "elements": [
    {"text": "获取验证码", "tag": "span",   "selector": "span.code-button",         "type": "text"},
    {"text": "输入手机号", "tag": "input",  "selector": "input[placeholder='输入手机号']", "type": "input"},
    {"text": "发布",       "tag": "button", "selector": "button.custom-button.bg-red", "type": "button"}
  ]
}
```

**使用时机**：当 AI 连续 2 次找不到目标选择器时，调用此接口获取全量文案地图，再从 `text` 字段定位目标元素，取对应 `selector` 传入 `/click` 或 `/type`。

---

## 5. 登录态检测（所有脚本执行前必须先调用）

```bash
POST /api/eval
{"expression": "!!document.querySelector('div.menu-list .popover_text')"}
```

返回 `{"result": true}` → 已登录，无需重复登录。
返回 `{"result": false}` → 未登录，执行登录流程。

---

## 6. 常用脚本

| 脚本 | 说明 |
|------|------|
| `scripts/login_phone.py` | 手机号 + 验证码登录 |
| `scripts/login_qrcode.py` | 扫码登录（附截图） |
| `scripts/publish.py` | 完整图文发布（上传图片→标题→正文→话题→原创→发布） |

---

## 7. 失败处理规则

- 接口返回 `503` → 服务未启动或页面已关闭，先用 `pm2 restart xhs-server` 恢复
- 接口返回 `400` → 选择器未找到，先调 `POST /api/screenshot` 截图确认当前页面状态
- 每个动作最多重试 1 次；连续 2 次失败先截图汇报，不盲目重试
