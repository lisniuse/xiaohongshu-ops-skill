<!--
  xiaohongshu-ops skill README
-->

# xiaohongshu-ops

小红书自动运营Skill，搭配Openclaw可以独立运营小红书账号

基于 **Playwright HTTP 服务**，AI 通过调用 HTTP API 控制浏览器，实现自动发布、自动回复、爆款笔记复刻等功能。第一次需要扫码/手机号登录，Session 持久化后续无需重复验证。

## What's New
- **最新**: 切换为 Playwright HTTP Server 架构，所有浏览器操作通过 HTTP API 完成，支持 PM2 持久运行
- **02.28**: 爆款笔记复刻，输入爆款笔记链接，分析爆款因素，生成类似的笔记，包含图文
- **02.27**: 局域网生图服务（Z-Image-Turbo）生成封面图，并通过图文发布流程发布（无需外部 API Key，调用本地 GPU 生图）

## 核心能力
- ✅ 自动发布笔记：上传图片、填写标题/正文/话题、原创声明、一键发布
- ✅ 自动回复评论：通知评论逐个回复
- ✅ 目标笔记下载：下载URL笔记图片和正文
- ✅ 爆款笔记复刻：输入爆款笔记链接，发布相似笔记
- ✅ persona.md：账号定位和人设，设定回复语气

---

## 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn playwright requests
playwright install chromium
```

### 2. 启动服务（强烈推荐 PM2）

PM2 可以让服务在后台持续运行，崩溃自动重启，无需手动维护：

```bash
# 安装 PM2（如未安装）
npm install -g pm2

# 启动服务（持久化用户 alice）
pm2 start xhs_server.py --interpreter python --name xhs-server -- --user alice

# 设置开机自启
pm2 save && pm2 startup

# 查看状态 / 日志
pm2 status
pm2 logs xhs-server
```

手动启动（临时调试）：
```bash
python xhs_server.py --user alice
```

服务启动后访问 **http://localhost:8989/docs** 查看完整接口文档。

### 3. 登录

```bash
# 扫码登录
python scripts/login_qrcode.py

# 手机号登录
python scripts/login_phone.py --phone 18676719432
```

### 4. 发布笔记

```bash
python scripts/publish.py \
  --files /path/to/img.png \
  --title "我的标题" \
  --content "正文内容" \
  --topics AI工具 效率 科技
```

---

## 使用示例

### 自动发布
```
帮我发布一篇关于太平年剧情讨论的小红书笔记
```

| 飞书自动发布 |
|---|
<br><img src="./assets/飞书自动发布笔记.jpg" alt="飞书自动发布笔记" width="100" /> |

### 自动回复评论
```
帮我检查小红书最新评论并回复
```

| 自动回复 |
|---|
<br><img src="./assets/自动回复.gif" alt="自动回复演示" width="420" />

### 爆款笔记复刻
```
帮我复刻爆款笔记 https://www.xiaohongshu.com/explore/XXXXXXX
```
| 输入爆款笔记URL | 复刻并发布 | 内容分析 |
|---|---|---|
<br><img src="./assets/爆款笔记.jpg" alt="输入的爆款笔记" width="420" /> | <br><img src="./assets/爆款笔记复刻结果.jpg" alt="复刻生成结果" width="420" /> | **Source Brief（精简拆解）**<br>- 原帖核心："按确认键"仪式感 + 低门槛参与<br>

---

## 给Openclaw单独开个账号
为了验证这个Skill究竟能不能独立运营小红书，我给Openclaw单独开了一个小红书账号
目前运营了20天，从0粉涨到450粉，暂未触发风控 / 限流

‼️ Openclaw发帖比我自己发火多了

| 小红书账号 | 首篇发布内容 + 自动回复 |
|---|---|
| <br><img src="./assets/小红书账号.jpg" alt="小红书账号" width="420" /> | <br><img src="./assets/自动发帖-回复.jpg" alt="第一个帖子发布+回复" width="420" /> |

---

## 安装
- 方法1: openclaw / codex 安装，复制以下内容发送
```
帮我安装这个skill，`https://github.com/Xiangyu-CAS/xiaohongshu-ops-skill`
```

- 方法2: clawhub安装
```
clawhub install xiaohongshu-ops
```

---

## 仓库结构

```
xiaohongshu-ops-skill/
├── SKILL.md                          # 技能主逻辑与执行规则（SOP、流程、边界）
├── persona.md                        # 人设/语气/回复风格
├── xhs_server.py                     # Playwright HTTP 控制服务（主程序）
├── scripts/
│   ├── login_phone.py                # 手机号登录
│   ├── login_qrcode.py               # 扫码登录
│   └── publish.py                    # 完整图文发布
├── references/
│   ├── xhs-server-setup.md           # 服务搭建、PM2、HTTP 接口速查 ← 新
│   ├── xhs-publish-flows.md          # 发布流程（HTTP API 版）
│   ├── xhs-runtime-rules.md          # 运行规则与约束
│   ├── xhs-comment-ops.md            # 评论互动与回复策略
│   ├── xhs-eval-patterns.md          # 通用 JS 提取模板
│   └── xhs-viral-copy-flow.md        # 爆款复刻链路
└── examples/
    ├── drama-watch/case.md           # 陪你看剧实例化流程
    └── reply-examples.md             # 近场评论对位回复样例
```

---

## Star 趋势

[![Star History Chart](https://api.star-history.com/svg?repos=Xiangyu-CAS/xiaohongshu-ops-skill&type=Date)](https://star-history.com/#Xiangyu-CAS/xiaohongshu-ops-skill&Date)
