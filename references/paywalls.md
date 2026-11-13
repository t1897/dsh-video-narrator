# 付费墙与受限站点

## 结论：不把 Bypass Paywalls Clean 装进 Skill

BPC 是一个 Chrome MV3 扩展，不是可被 Python 直接调用的抓取库：

- `background.js` 用 `declarativeNetRequest` 拦截站点资源（例如 Bloomberg 的 `bwbx.io` 付费墙 CSS）；
- `contentScript_en.js` 在页面 DOM 里移除 `html/body` 的付费墙 class、重建文章节点；
- 它依赖真实 Chromium、页面 JS、host permissions 和站点 cookie，无法在 `trafilatura`/`requests` 的 HTTP 路径里复现。

把它塞进 Skill 还会带来两个问题：需要 Playwright/Chromium（与“轻量、单进程”目标冲突），以及绕过付费墙可能违反站点条款/版权。**因此本 Skill 不捆绑 BPC，也不实现付费墙绕过。**

## 支持的四种合规路径

1. **免费转载/通讯社副本**  
   同一篇 Bloomberg 文章常有 Business Times、Economic Times、The Edge 等转载。优先用转载 URL 抓正文，并把原始 URL 记到 `project.json.source_url`。

2. **用户已登录的浏览器会话**  
   如果用户有订阅，用其 Chrome profile / storage state / CDP 打开页面，再交给 `trafilatura`。这属于“用用户自己的访问权”，不是绕过。
   - 预留变量：`VCS_BROWSER_CDP_URL`、`VCS_BROWSER_STORAGE_STATE`。
   - 实现优先级低于 M3，不在 v1 强制依赖。

3. **保存 HTML 后离线抽取**  
   用户在浏览器里打开文章（可手动登录/展开全文），保存为 HTML，然后：

   ```bash
   vcs ingest --input "https://www.bloomberg.com/news/articles/..." \
     --html /path/to/saved.html --out runs/bt-article
   ```

4. **用户提供的 PDF / 纯文本**  
   最稳，直接 `vcs ingest --input file.pdf` 或 `--type text`。

## 本次实测

- Bloomberg 原始 URL：HTTP 403 + “Are you a robot?”（PerimeterX）。
- Business Times 转载：HTTP 200，`trafilatura` 抽取约 8k 字符，正文完整到 `BLOOMBERG` 结尾。
- 因此项目 `runs/bt-article` 使用转载正文，`project.json` 同时保留：
  - `source_url`: Bloomberg 原始 URL
  - `syndicated_url`: Business Times 转载 URL

## 如果用户坚持用 BPC

让用户在自己的浏览器里使用扩展并保存页面 HTML，然后走 `--html`。不要把扩展二进制、crx 或站点规则复制进 Skill；也不要承诺“任意付费墙都能抓”。
