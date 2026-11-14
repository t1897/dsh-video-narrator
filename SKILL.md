---
name: video-narrator
description: 把视频、视频链接、文章链接、PDF 或纯文本转成带配图与配音的口播视频。产出清洗后的 Markdown 文稿、分段口播稿、10 个标签的 metadata.json、逐段配图与 TTS 音频，并用 ffmpeg 合成 16:9 横屏或 9:16 竖屏成片。用户提到“文章转视频”“视频转视频”“口播视频”“AI 配音”“自动配图”“横屏/竖屏短视频”“PDF 转视频”时使用。
---

# Video Narrator

把「素材」变成「可发布的口播视频」：文稿 → 分段口播稿 → 标题/标签 → 逐段配图 + 配音 → ffmpeg 合成 → 按标题命名。

## 强制：开始前先弹参数确认

**这是本 Skill 的第一步，优先于下面所有步骤。** 在任何 `ingest` / `asr` / `text` / `images` / `tts` / `compose`、写文件或创建项目之前，必须先调用 `ask_user_question`，和用户确认参数。

一次性问这 4 项：

| id | 问题 | 选项（默认在前） |
|---|---|---|
| `orientation` | 画幅？ | 竖屏 9:16（默认）/ 横屏 16:9 / 自定义宽高 |
| `duration` | 视频时长？ | 固定 6 分钟（默认）/ 3–5 分钟 / 5–8 分钟 / 不限 / 自定义 |
| `segment` | 每段多少秒？ | 20–40 秒（默认）/ 25–35 秒 / 自定义 |
| `voice` | 音色和风格？ | female（Tina，默认）/ male（hugo）/ 自定义参考音；风格 cinematic（默认）/ documentary / anime |

规则：

- **不要跳过对话框直接开跑。** 即使用户在请求里已经写了“竖屏、5 分钟”，也要用一题汇总确认（“确认开始 / 修改参数”），不要静默采用。
- 用户跳过某一项时用默认值，但在开始前明确复述最终参数。
- 如果安装了 Client UI，左侧边栏的「视频」工作台面板会生成带 `[VCS_PARAMS_CONFIRMED]` 的消息；收到这种消息时不要再弹对话框，复述参数后直接开始。
- 把答案传给 `vcs init` / `vcs ingest` / `vcs config`：`--orientation`、`--duration`、`--segment-range`、`--voice`、`--style`；自定义参考音用 `--voice-ref`（并尽量带 `--voice-ref-text`）。
- 没有 `ask_user_question` 工具的环境（例如纯 CLI/headless），在对话中逐项询问，或让用户显式传齐参数；**不能默认静默开始**。
- 如果用户消息包含 `[VCS_PARAMS_CONFIRMED]`（来自左侧边栏的“视频”工作台面板），说明参数已经通过 UI 确认：**不要再调用 `ask_user_question`**，复述一次参数后直接开始；只有素材缺失时才问素材。
- 参数确认完成后才进入“完整流程”。

## 当前实现状态

**v1.0 已完成**（2026-11-12）：6 项单测通过，4 条真实成片（YouTube ×2 / 文章 / PDF），支持生成前配置、多 API 回退、来源目录命名与中间文件清理。

- **M0**：`doctor`、`init`、`run --mock`、`status`；mock 文本/图片/TTS + 真实 ffmpeg 合成。
- **M1**：`ingest`（本地视频/YouTube/文章/PDF/文本）+ `asr`（Qwen3-ASR-1.7B，MLX）。
- **M2**：Agent 直接写 `02_transcript.md` / `03_script.json` / `04_metadata.json` / `05_image_prompts.json`，或 `vcs text` 调多个自定义 API；`validate` 做结构、字数、时长、10 tags 校验。
- **M3**：`images`（魔搭 ModelScope 异步 API）、`tts`（Qwen3-TTS-1.7B，MLX）、`compose`（ffmpeg 逐段 + concat + 按标题命名）。
- 四个真实输入已跑通：YouTube ×2、Bloomberg 文章（Business Times 免费转载正文）、Foreign Affairs PDF。

实测结果（1080×1920 / 30fps / h264+aac）：

| 输入 | 成片 | 段数 |
|---|---|---|
| YouTube 11.5 分钟访谈 | 129.2 秒 / 15.1MB | 6 |
| Bloomberg / Megaspeed 文章 | 123.1 秒 / 14.5MB | 6 |
| Foreign Affairs PDF | 123.8 秒 / 15.6MB | 6 |

已知限制：
- 魔搭生图需要 Key：单 Key 用 `VCS_MODELSCOPE_API_KEY`，多账号用 `providers.json` + `VCS_MODELSCOPE_CN_KEY` / `VCS_MODELSCOPE_INTL_KEY`；否则用 `--provider mock`。
- Qwen3-TTS-1.7B 峰值内存约 9–10GB，生成 1 分钟语音约 3 倍实时。
- 音色一致性靠固定参考音 + seed；TTS 必须提供参考音（内置 female/male 样本或 `--voice-ref`），不再使用无参考音的默认音色。
- 文本既可由 Agent 写，也可用 `vcs text` 调自定义 API；多个 API 按 `providers.json` 顺序回退。

## 环境

需要 Python 3.12/3.13、ffmpeg/ffprobe、yt-dlp。建议两个解释器（也可以合并成一个）：

```bash
TEXT_PY=.venv/bin/python          # 需要 pypdf + trafilatura（ingest/validate/images/compose）
MLX_PY=~/Documents/Projects/venv/bin/python  # 需要 mlx-audio + mlx-qwen3-asr（asr/tts）
export HF_HOME="${HF_HOME:-$HOME/.cache/vcs/hf}"
```

## 自定义 API 与多 API 回退

复制模板并填 Key（`providers.json` 已被 gitignore，Key 建议放 `.env`）：

```bash
cp providers.example.json providers.json
# 编辑 providers.json 的 base_url/model/api_key_env
vcs providers --file providers.json    # 只显示 key=set/missing，不打印 Key
```

**文本 API（OpenAI 兼容）**

```bash
vcs text --project runs/demo --stage all
# 或单独跑：cleanup / script / metadata / prompts
```

- 按 `providers.json` 里 `text` 数组的顺序尝试；`provider: "agent"` 会被跳过（那是宿主 Agent 模式）。
- 第一个 API 失败（401/429/5xx/超时/JSON 不合法）自动换下一个；全部失败才报错。
- 兼容任意 OpenAI 格式 `/v1/chat/completions`；`base_url` 带不带 `/v1` 都行。

**生图（魔搭国内/国际、多账号）**

```bash
vcs images --project runs/demo --providers providers.json
```

- 按 `image` 数组顺序尝试；单张图第一个 Key 额度用光/401/429/超时/任务失败，就换下一个 Key。
- 某个 profile 失败后会在本项目的剩余场景里被跳过，避免反复撞同一个额度。
- 国内：`https://api-inference.modelscope.cn`；国际：`https://api-inference.modelscope.ai`；两者可混排。
- 不同账号用不同 `api_key_env`（如 `VCS_MODELSCOPE_CN_KEY`、`VCS_MODELSCOPE_INTL_KEY`）。
- `providers.json` 搜索顺序：`--providers/--file` > `VCS_PROVIDERS_FILE` > 项目目录 > 当前目录 > Skill 目录 > `~/.config/vcs/providers.json`。

## 生成前先问用户

开始生图/配音之前，先确认这 4 项（也可以说“用默认”）：

| 项 | 选项 | 对应参数 |
|---|---|---|
| 画幅 | 竖屏 9:16 / 横屏 16:9 / 自定义宽高 | `--orientation portrait` 或 `landscape`、`--width/--height` |
| 时长 | 固定 N 分钟 / N–M 分钟 / 不限 | `--duration 6`、`--duration 5-8`、`--duration unlimited` |
| 每段 | 默认 20–40 秒，可改 | `--segment-range 20-40` |
| 音色/风格 | female/male；cinematic 等 | `--voice`、`--style` |

示例：

```bash
# 竖屏、固定 6 分钟
$TEXT_PY scripts/vcs.py init --input ... --orientation portrait --duration 6

# 横屏、5–8 分钟、每段 25–35 秒
$TEXT_PY scripts/vcs.py init --input ... --orientation landscape --duration 5-8 --segment-range 25-35

# 不限时长（仍保留 max_segments=60 的安全上限）
$TEXT_PY scripts/vcs.py init --input ... --duration unlimited

# 自定义分辨率
$TEXT_PY scripts/vcs.py init --input ... --orientation portrait --width 1080 --height 1920

# 已有项目改配置（会删除受影响的产物，保留 transcript.md / source）
$TEXT_PY scripts/vcs.py config --project runs/demo --orientation landscape --duration 5-8
```

终端里也可以 `--interactive` 逐项询问；Agent 模式下由 Agent 在对话里问，再把答案传给命令。

## 快速开始

```bash
$TEXT_PY scripts/vcs.py doctor

# 1) 采集
$TEXT_PY scripts/vcs.py ingest --input "https://www.youtube.com/watch?v=..." --out runs/demo
$MLX_PY scripts/vcs.py asr --project runs/demo --language English   # 文章/PDF 跳过

# 2) 文本阶段由 Agent 写文件，然后校验
$TEXT_PY scripts/vcs.py validate --project runs/demo

# 3) 生图 / 配音 / 合成
$TEXT_PY scripts/vcs.py images --project runs/demo
$MLX_PY scripts/vcs.py tts --project runs/demo
$TEXT_PY scripts/vcs.py compose --project runs/demo
```

产物：`projects/<来源标签>_<MMDDYYYY>_<metadata.title>/final/<metadata.title>.mp4`（不传 `--out` 时）。

## 默认参数

| 参数 | 默认 |
|---|---|
| 时长 | 固定 6 分钟；可 `--duration 5-8` 或 `unlimited` |
| 分段 | 20–40 秒，目标 30 秒（`--segment-range` / `--segment`） |
| 画幅 | 9:16 竖屏 1080×1920；可横屏或自定义 `--width/--height` |
| 语言 | 中文（`--language`） |
| 音色 | female/male（`--voice`）；参考音必需（内置样本或 `--voice-ref`）+ seed |
| 生图 | 魔搭 `Tongyi-MAI/Z-Image-Turbo`，质量档 `Qwen/Qwen-Image-2512` |
| 字幕 | v1 不生成 |
| 文本 | Agent 直接写文件；或 `vcs text` 调多个自定义 API |

## 完整流程（已实现）

1. **ingest**：本地视频/视频链接 → 抽音频；文章链接 → trafilatura；PDF → pypdf；纯文本 → 直接。
2. **asr**：Qwen3-ASR-1.7B（MLX）转写，30 秒块切分；输出 `01_transcript.raw.txt`。
3. **cleanup**：读 `references/prompts/01_cleanup.md`，写 `02_transcript.md`；可由 Agent 写，也可 `vcs text --stage all` 调自定义 API。
4. **script**：读 `02_script.md` + 目标时长/分段/语速，写 `03_script.json`（`segments[]`，无 `parts`）。
5. **metadata**：读 `03_metadata.md`，写 `04_metadata.json`（title + description + 恰好 10 个 tags）。
6. **prompts**：按画幅读 `04_image_16x9.md` 或 `05_image_9x16.md`，写 `05_image_prompts.json`。
7. **images**：逐段调魔搭 API（异步任务 → 轮询 → 下载），`06_images/scene_001.png`。
8. **tts**：逐段 Qwen3-TTS-1.7B，固定 seed/采样参数；参考音必需（默认 `assets/voice_female.mp3` / `voice_male.mp3`，可 `--voice-ref` 覆盖），`audio/scene_001.wav`。
9. **compose**：每段图 + 音 → `clips/scene_001.mp4`，`concat -c copy` 合并；默认清理 `audio/`、`clips/`、`logs/`。
10. **finalize**：`metadata.title` 安全化后直接输出根目录 `07_<标题>.mp4`。

## Agent 模式约定

- 每个文本阶段只做一件事：读对应 prompt，写目标文件，然后跑 `vcs validate --project <dir>`；文件名按 01–05 的步骤前缀。
- `03_script.json` 的 schema 不要改；不要写 `parts`；每段 `narration` 60–220 字（中文）。
- `04_metadata.json` 的 `tags` 必须恰好 10 个；标题会作为 `07_` 文件名的一部分，避免 `/ \ : * ? " < > |`。
- 用户只改画幅时，只重跑 prompts/images/compose，不要重写文稿和配音。
- 失败时先读 `logs/run.log` 与 `vcs status`，不要手动删除 `audio/`、`06_images/` 以“重来”。

## 输出目录格式

```text
projects/
└── YouTube_11122026_英伟达最大风险，不是芯片，而是黄仁勋/
    ├── project.json
    ├── 01_transcript.raw.txt
    ├── 02_transcript.md
    ├── 03_script.json
    ├── 04_metadata.json       # 含 source
    ├── 05_image_prompts.json
    ├── 06_images/scene_001.png
    ├── 07_<标题>.mp4          # 最终成片，直接在根目录
    ├── source/xxx.pdf         # 仅 PDF 保留
    └── state.json
```

- 第一段：文章取域名（`businesstimes.com.sg`）、视频取平台（`YouTube`/`Bilibili`）、PDF 用 `PDF`。
- 第二段：`MMDDYYYY`（无分隔符的月日年，如 `11122026`）。
- 第三段：metadata 生成后追加标题；改标题后跑 `vcs rename --project ...`。
- `--out` 显式指定目录时不自动改名；可用 `vcs rename` 迁移。
- `compose` 默认删除 `audio/`、`clips/`、`logs/`、临时文件；`--keep-intermediates` 可保留。也可单独跑 `vcs clean`。
- `04_metadata.json.source` 记录：`type`、`label`、`platform`、`domain`、`url`、`syndicated_url`、`file`。

## 质量检查

- `ffprobe`：竖屏 1080×1920 / 横屏 1920×1080，30fps，h264 + aac。
- 总时长 ≈ 各段音频之和；单段结尾不被截断（TTS 尾部静音 350ms）。
- 图片尺寸正确、无文字/水印/分屏；同一视频风格一致。
- 最终文件名 = `07_` + `metadata.title` 安全化结果，直接在项目根目录。
- 音色：同一参考音、同一 seed；段间 250–350ms 留白。

## 故障排查

| 现象 | 处理 |
|---|---|
| `ffmpeg not found` | `brew install ffmpeg`；再跑 `doctor` |
| HF 缓存为空 | 先下载 ASR/TTS 模型；`doctor` 会显示缓存大小 |
| 魔搭 401/403 | 设置 `VCS_MODELSCOPE_API_KEY`；确认 token 有推理权限 |
| 文章 403 / 机器人墙 | 用免费转载副本，或浏览器保存 HTML 后 `vcs ingest --html`；见 `references/paywalls.md` |
| 魔搭任务超时 | 单任务 600s 超时；降低并发或换 `Qwen/Qwen-Image-2512` |
| concat 花屏/音画不同步 | 所有 clip 必须同分辨率/fps/采样率/GOP；不要混用不同编码参数 |
| 时长偏差 >15% | 校准 `chars_per_second`；重跑 script，不要直接裁音频 |

## 参考文件

- `references/providers.md`：魔搭异步 API、MLX ASR/TTS、文本双模式。
- `references/ffmpeg.md`：逐段合成、concat、横竖屏参数。
- `references/paywalls.md`：Bloomberg 等受限站点的合规采集路径（不捆绑 BPC）。
- `references/prompts/`：5 个文本/图片 Prompt 模板。
