# XHS 运行规则（引用自技能主文）

> 所有浏览器操作均通过 HTTP API 服务（`xhs_server.py`）完成。
> 服务搭建与 PM2 持久运行方法见 `references/xhs-server-setup.md`。

---

## 0.1 服务就绪校验（每次任务开始前必须执行）

```bash
GET /api/status
```

- 返回正常 → 继续执行
- 返回 `503 页面已关闭` → 先 `pm2 restart xhs-server`，等待 3 秒后重试
- 连接被拒绝 → 服务未启动，执行 `pm2 start xhs-server` 或手动启动

---

## 0.2 登录态校验（每次任务开始前必须执行）

```bash
POST /api/eval
{"expression": "!!document.querySelector('div.menu-list .popover_text')"}
```

- `true` → 已登录，继续任务
- `false` → 执行登录流程（`scripts/login_qrcode.py` 或 `scripts/login_phone.py`）

---

## 0.3 API 调用约束

- 每个动作最多重试 **1 次**；第二次失败先截图汇报，改稳健路径
- 失败时第一步永远是：`POST /api/screenshot` 截图确认当前页面状态
- 不做盲目连续重试；保留已完成进度，报告需手动操作的单一步骤

---

## 0.4 截图约束

- 只在关键节点截图：登录确认、到发布页、填写完成、发布前停顿
- 避免 `full_page: true`（除用户要求整页归档）
- 截图路径会在响应中返回，可直接引用

---

## 1. 搜索与浏览约束

1. 仅从搜索结果页点击进入帖子，禁止直接 `navigate` 到 `/explore/<id>`
2. 默认跳过本账号作者内容（避免自刷）
3. 进入后先校验：不是 404、可见评论/互动信息、可识别标题
4. 进入方式优先点卡片本体，避免点头像/作者名导致跳错
5. 评论控件若为 `contenteditable`，`/api/type` 会自动处理（无需额外操作）
6. 两次点击失败或 404 后返回搜索页换下一条，不重试同链接

---

## 2. 回放与降级

- 选择器失效时先 `POST /api/screenshot` 更新页面状态后再继续，不盲跑旧路径
- 关键页（创作页、探索页、用户页）优先复用已导航页面，减少重复 `navigate`
- 先告知用户"已达异常节点"，避免误操作
- 发布页关键动作失败时：
  1. `POST /api/screenshot` 截图确认
  2. 同动作最多再试 1 次（可换 `:has-text()` 方式重新定位）
  3. 仍失败则调用 `GET /api/elements` 获取页面全量文案地图，从 `text` 字段找到目标，取 `selector` 重试
  4. 仍失败则提示用户手动完成最后一步

### 选择器失效降级流程（优先级从高到低）

```
1. 原选择器重试一次
2. 改用 :has-text('按钮文字') 方式定位
3. GET /api/elements → 从文案地图取 selector
4. 截图汇报 + 提示用户手动操作
```

---

## 3. 轮播图抓取规则

- 禁止直接取页面第一个 `.img-container`
- 必须优先：`POST /api/eval` + `document.querySelector('.swiper-slide-active:not(.swiper-slide-duplicate) .img-container img')?.src`
- 抓图后核对 URL 末段 key 是否与目标封面一致；不一致则重新抓取

---

## 4. PM2 运维速查

```bash
pm2 status                    # 查看服务状态
pm2 logs xhs-server           # 查看实时日志
pm2 restart xhs-server        # 重启（页面关闭/崩溃后使用）
pm2 stop xhs-server           # 停止
pm2 start xhs-server          # 启动已注册的进程
```
