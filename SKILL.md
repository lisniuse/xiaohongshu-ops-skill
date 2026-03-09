---
name: xiaohongshu-ops
description: "End-to-end Xiaohongshu operations including positioning, topic research, content production, publish execution, and post-incident recovery. Reusable across verticals with templates and a concrete 陪你看剧 case preset."
---

# Openclaw 小红书运营技能（通用版）

目标：构建可复用的"小红书运营"流程，让任何账号类型都能复用同一套动作框架。

## 适用范围（默认即通用流程）

- 账号定位与内容方向
- 选题产出与争议点挖掘
- 竞品/同类账号对标
- 小红书发布前演练与内容交付
- 发布后快速复盘（互动结构、评论回复、热点追踪）
- Viral Copy 链路（输入 URL，高贴合学习封面/配图、标题、正文并生成可发布近似结构笔记）

将每类账号的行业细节作为"案例模块（case module）"挂载到通用流程中。

## 常用术语

- `选题`：可发布、可讨论、可转发的内容切入点
- `引流钩子`：标题/开头一句用于触发停留与点击
- `结构化输出`：标题、正文、互动问句、话题、标签五元组
- `快照`：调用 `POST /api/screenshot` 验证页面状态的关键证据
- `回放`：流程失败后重试或改道执行

## 0) 启动与环境校验（所有任务都遵循）

执行前先按 `references/xhs-runtime-rules.md` 中"运行规则"执行，优先遵循失败可复用顺序。

**浏览器控制方式**：所有浏览器操作通过 HTTP API（`xhs_server.py`）完成，服务默认运行在 `http://127.0.0.1:8989`。
搭建方式与 PM2 持久运行配置见 `references/xhs-server-setup.md`。

**强烈推荐使用 PM2 启动并维持服务持续运行**（自动重启、开机自启、日志管理）：
```bash
pm2 start xhs_server.py --interpreter python --name xhs-server -- --user alice
```

启动后依次执行：

1. `GET /api/status` — 确认服务就绪
2. `POST /api/eval {"expression": "!!document.querySelector('div.menu-list .popover_text')"}` — 确认登录态
3. 未登录则执行 `scripts/login_qrcode.py` 或 `scripts/login_phone.py`

每个动作最多重试 1 次；失败先调 `POST /api/screenshot` 截图确认状态，再改稳健路径汇报。

## 1) 技能默认行为（所有任务都遵循）

- **先读本技能目录下的 `persona.md`**（小红书平台专用人设/语气/发布与回复风格）。所有对外文案（发帖/评论回复/私信话术）都必须遵循。
- 优先输出可执行的 SOP 而非一次性内容稿
- 语言优先"能对话"而不是"写报告"：短句、口语、站位明确、可引导评论
- 所有输出默认保留"可追问点"，用于评论区继续延展

## 2) 账号定位（可复用）

每个账号先确认 4 个变量：

- 目标用户：年龄/场景/痛点（如「下班后碎片时间」「追星讨论人群」）
- 内容价值主张：每篇给用户什么（观点、情绪价值、实操建议）
- 差异化角度：同类账号不做什么、你做什么
- 风格规范：语气、长度、冲突边界（避免过激）

输出：

- 人设关键词（3-5）
- 内容支柱（3 个）
- 口头禅/固定句式（2-3 个）
- 不能碰底线（红线）清单（剧透、人身攻击、虚假承诺）

## 3) 通用选题与对标流程

### A. 平台侧抓取信号（可并行）

1. 先在小红书抓同题材高互动内容（点赞/收藏/评论高于近期平均值）
2. 记录可复用字段：`title`, `hook`, `angle`, `结构标签`, `评论信号`, `互动CTA`, `标签组`
3. 汇总前 10-20 条到候选池

### B. 需求侧补充信号（行业/场景）

1. 按主题去主流平台/社媒抓"评论区观点分歧"
2. 抽取支持/反对/中性观点各一组
3. 输出可发文争论点（争议但可控）

### C. 形成选题清单（每轮至少 3 条）

每条选题包含：

- 选题标题（20 字内可选）
- 观点标签（支持/反对/中性）
- 预计互动钩子
- 证据来源（哪组高互动数据）
- 风险提示（是否容易踩线）

## 3.5) 搜索并浏览（新增操作类型）

按 `references/xhs-runtime-rules.md` 的搜索与评论入口章节执行。

- 只允许从搜索结果页进入帖子；
- 优先通知/回复场景前先对位校验。
- 连续失败回退策略见引用文件。

## 3.6) Viral Copy（URL → 新笔记）

按 `references/xhs-viral-copy-flow.md` 执行。

- 输入：目标爆款笔记 URL（可多条）。
- 输出：1 套可发布素材（封面/配图方案 + 标题 + 正文 + 话题）。
- 复刻原则：高贴合主题与结构（标题句式、封面信息层级、正文节奏、互动机制），同时避免逐字照抄与素材侵权。

## 4) 通用内容模板（小红书）

每次产出至少 2 个备选：

- 标题（争议/立场/反问，≤20字优先）
- 开头钩子（1-2 句）
- 正文（3 段：观点→证据→反方）
- 互动提问（1 句）
- 话题（5-8 个）
- 风险标注（是否剧透 / 引战边界 / 版权风险）

## 5) 通用发布链路

详细发布执行路径请直接按 `references/xhs-publish-flows.md` 执行，避免重复维护。

发布前必须满足的核心点：

- `GET /api/status` 确认服务就绪，`POST /api/eval` 确认已登录。
- 明确发布类型（视频 / 图文 / 长文），三要素：封面、标题、正文。
- 到达"发布"按钮可见处停手，默认不直接点击发布。
- 若涉及截图确认，调用 `POST /api/screenshot` 获取截图路径，附给用户确认后再发布。

**一键发布脚本**（AI 可直接组装参数调用）：
```bash
python scripts/publish.py \
  --files /path/to/img.png \
  --title "标题" \
  --content "正文" \
  --topics 话题1 话题2 话题3
```

## 6) 评论与回复（轻量）

评论检查与回复统一遵循 `references/xhs-comment-ops.md`，并结合 `examples/reply-examples.md` 作文案风格。

- 默认优先走通知页，先对位后输入后发送。
- 默认 one-send-per-turn（如无明确要求不连发）。
- 长度、隐性承诺、风控停损点等风险控制项请以引用文件为准。

## 7) 失败与修复（必须遵循）

- 自动化失败先重试一次（同策略）
- 仍失败则：先 `POST /api/screenshot` 截图确认状态，再换稳妥同义路径
- 服务不可达（连接被拒 / 503）→ `pm2 restart xhs-server` 后重试
- 不做无效重复动作；保留当前进度可复用，报告一次用户需手动的单一动作

## 8) 通用提取示例（Eval）

通用字段提取脚本示例见 `references/xhs-eval-patterns.md`。

通过 HTTP 接口执行：
```bash
POST /api/eval
{"expression": "(() => { /* 你的 JS */ })()"}
```

## 9) 具体案例：陪你看剧（保留为特例）

### 使用方式

本技能主文件保留通用框架；垂直行业经验放在 `examples/` 目录，按内容类型选用：

- 先按《通用流程》跑一遍
- 再加载对应案例文件补齐行业特殊动作

当前已可用案例：

- `examples/drama-watch/case.md`（陪你看剧账号）

每个内容类型按目录组织，文件命名可为：

- `examples/<vertical>/<vertical>.md`（推荐）
- 或 `examples/<vertical>/README.md`

- `examples/lifestyle/`（待补充）
- `examples/cosmetics/`（待补充）
- `examples/fitness/`（待补充）

---

## 实操经验（持续有效）

- **服务用 PM2 管理**：`pm2 start xhs_server.py --interpreter python --name xhs-server -- --user <名字>`，开机自启保证服务常驻
- **固定 `--user` 参数**：session 持久化在 `sessions/<名字>/`，重启后无需重新登录
- 文字配图是稳定写入口，配合 `/api/type` 直接输入封面文案
- 话题输入：正文末尾换行后每个话题单独 `/api/type` + `"append": true`，再按 Enter 确认
- `/api/eval` 批量读取页面数据时，尽量用精确选择器减少抓取量
- 关键步骤前调一次 `POST /api/screenshot`，可用于复盘与问题定位
- 「发布」按钮可见 ≠ 发布成功；必须明确标注"到发布页停手"
- 若出现新类型评论节奏问题，优先减少每小时回复密度而非提高频率

## 运营成熟路径（可选）

- 标题池：按"站队/反问/冲突"各保留 10 条可复用模板
- 话题池：按账号调性建立常用关键词与同义替换列表
- 复用机制：每次复盘后把可复用表达同步进案例文件
