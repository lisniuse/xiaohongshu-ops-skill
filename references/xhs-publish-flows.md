# XHS Publish Flows

本文件拆分并细化「发布链路」的操作步骤，供 `SKILL.md` 按需引用。

> **执行方式**：所有步骤通过调用 HTTP API（`xhs_server.py`）完成，不直接操作浏览器。
> 接口速查见 `references/xhs-server-setup.md`，服务地址默认 `http://127.0.0.1:8989`。

---

## 0. 总览

发布类型：
- 图文（推荐默认）
- 视频
- 长文

三要素（发布前必须齐全）：
1. 封面 / 图片
2. 标题（≤20 字）
3. 正文

---

## 1. 图文发布（推荐默认）

### 1.1 完整图文发布流程（HTTP API）

```
Step 1  POST /api/navigate     跳转图文发布页
        {"url": "https://creator.xiaohongshu.com/publish/publish?from=menu&target=image"}

Step 2  POST /api/upload_file  上传图片（支持多张）
        {"selector": "input[type='file']", "files": ["/path/to/img.png"]}

Step 3  POST /api/click        点击标题输入框
        {"selector": "input.d-text[placeholder='填写标题会有更多赞哦']"}

        POST /api/type         输入标题
        {"selector": "input.d-text[placeholder='填写标题会有更多赞哦']", "text": "标题内容"}

Step 4  POST /api/type         输入正文（自动兼容 ProseMirror 富文本）
        {"selector": ".tiptap.ProseMirror[contenteditable='true']", "text": "正文内容"}

Step 5  POST /api/key          换行后输入话题
        {"key": "Enter"}
        POST /api/type
        {"selector": ".tiptap.ProseMirror[contenteditable='true']", "text": "#话题名", "append": true}
        POST /api/key
        {"key": "Enter"}
        （每个话题重复一次）

Step 6  POST /api/click        开启原创声明
        {"selector": ".custom-switch-card:has(.has-tips) .d-switch-simulator.unchecked"}

Step 7  POST /api/click        弹窗勾选协议
        {"selector": ".d-checkbox.bg-red .d-checkbox-simulator"}

Step 8  POST /api/click        点击「声明原创」
        {"selector": "button.custom-button.bg-red:has-text('声明原创')"}

Step 9  POST /api/click        点击「发布」
        {"selector": "button.custom-button.bg-red:has-text('发布')"}
```

> **一键脚本**（AI 可直接调用）：
> ```bash
> python scripts/publish.py \
>   --files /path/to/img.png \
>   --title "标题" \
>   --content "正文" \
>   --topics 话题1 话题2 话题3
> ```

### 1.2 半程预发（不发布，停在发布按钮）

满足以下条件即视为"半程预发完成"：
- 已完成图片上传（`/api/upload_file` 成功）
- 已填写标题与正文
- 跳过 Step 9，停在「发布」按钮可见处

### 1.3 外部生图服务 + 图文发布

1. 调用局域网生图服务（`POST http://192.168.31.110:8088/api/generate`），保存返回的 PNG
2. 将图片路径传入 `/api/upload_file` 的 `files` 字段
3. 后续按 1.1 流程继续

---

## 2. 视频发布

```
Step 1  POST /api/navigate     跳转视频发布页
Step 2  POST /api/upload_file  上传视频文件
        {"selector": "input[type='file']", "files": ["/path/to/video.mp4"]}
Step 3  补齐封面/标题/正文（同图文 Step 3-4）
Step 4  停在发布按钮，等待用户确认后执行 Step 5
Step 5  POST /api/click        点击「发布」
```

---

## 3. 长文发布

```
Step 1  POST /api/navigate     跳转长文发布页
Step 2  POST /api/type         填写长文标题
Step 3  POST /api/type         填写正文结构（append: true 追加段落）
Step 4  停在发布按钮，等待用户确认
```

> 若用户目标是图文，避免误走长文链路。

---

## 4. 常见问题与处理

| 问题 | 处理方式 |
|------|----------|
| 选择器找不到元素（400） | `POST /api/screenshot` 截图确认当前页面，重新定位选择器 |
| 页面已关闭（503） | `pm2 restart xhs-server` 重启服务 |
| 标题超 20 字 | 调用 `/api/type` 清空重填（不传 `append`） |
| 图文误入长文链路 | `POST /api/navigate` 重新跳转发布页 |
| 上传图片路径报错 | 确认文件绝对路径存在，Windows 路径使用正斜杠或双反斜杠 |
| 点击「发布」元素失效 | 先 `POST /api/screenshot` 截图确认状态，用 `:has-text('发布')` 重定位 |
