# Providers

## 文本阶段

| 模式 | 用法 | 行为 |
|---|---|---|
| `agent`（默认） | Agent 直接写文件 | 读 `references/prompts/*.md`，写 `transcript.md` / `script.json` / `metadata.json` / `image_prompts.json`，再跑 `vcs validate` |
| `http` | `vcs text --project ... --stage all` | 按 `providers.json` 的 `text` 顺序调 OpenAI 兼容 `/v1/chat/completions`，失败自动换下一个 |

`agent` profile 会被 `vcs text` 跳过；要自动跑文本，至少配置一个 `provider: "openai"` 的 profile。

## providers.json（多 API 顺序回退）

复制 `providers.example.json` 为 `providers.json`（已被 gitignore），Key 放 `.env`：

```json
{
  "text": [
    {"name": "agent", "provider": "agent"},
    {"name": "primary", "provider": "openai", "base_url": "https://api.openai.com/v1", "api_key_env": "VCS_LLM_1_KEY", "model": "gpt-4o-mini"},
    {"name": "backup", "provider": "openai", "base_url": "https://api.deepseek.com/v1", "api_key_env": "VCS_LLM_2_KEY", "model": "deepseek-chat"}
  ],
  "image": [
    {"name": "modelscope-cn", "provider": "modelscope", "base_url": "https://api-inference.modelscope.cn", "api_key_env": "VCS_MODELSCOPE_CN_KEY", "model": "Tongyi-MAI/Z-Image-Turbo"},
    {"name": "modelscope-intl", "provider": "modelscope", "base_url": "https://api-inference.modelscope.ai", "api_key_env": "VCS_MODELSCOPE_INTL_KEY", "model": "Tongyi-MAI/Z-Image-Turbo"}
  ]
}
```

- `api_key_env` 指向环境变量；也可以直接写 `api_key`（不推荐）。
- 搜索顺序：`--providers` / `--file` > `VCS_PROVIDERS_FILE` > `<project>/providers.json` > `./providers.json` > Skill 目录 > `~/.config/vcs/providers.json`。
- 文本：401/429/5xx/超时/JSON 不合法 → 下一个；全部失败才报错。部分 API 不支持 `response_format`，遇到 400/422 会去掉它重试一次。
- 生图：每个场景按 `image` 顺序试；某个 profile 失败后在本项目剩余场景中跳过，避免反复撞额度。
- 查看配置（不打印 Key）：`vcs providers --file providers.json`。

## ASR

默认：`mlx-community/Qwen3-ASR-1.7B-8bit`（备选 0.6B）。

- 30 秒块切分（v1 无重叠；长音频按块串行转写）。
- 语言 `en`/`zh` 等；热词 `--hotwords` 可选。
- 输出 `transcript.raw.txt`。
- 兜底：`faster-whisper large-v3-turbo`（CPU，MIT）。

## TTS

默认：`mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16`（备选 0.6B）。

一致性参数（每段都相同）：

- 参考音（必需）：5–10 秒、干净、同语言、24kHz 单声道；整条视频一个。默认使用内置 `assets/voice_female.mp3` / `voice_male.mp3`，也可通过 `--voice-ref` 指定。
- `seed=42`、`temperature=0.35`、`top_p=0.85`、`speed=1.0`。
- 复用一次 `create_voice_clone_prompt`，不要每段重新克隆。
- 文本尾部加 `。。`（只发给模型，不进文稿）；生成后补 350ms 静音。
- 输出 24kHz 单声道 WAV；合成时统一转 48kHz 立体声 AAC。
- 单段不足 20 秒会补静音到 20 秒，保证分段落在 20–40 秒。

## 生图

默认：魔搭 ModelScope，模型 `Tongyi-MAI/Z-Image-Turbo`；质量档 `Qwen/Qwen-Image-2512`。

- 国内：`https://api-inference.modelscope.cn`；国际：`https://api-inference.modelscope.ai`。
- Endpoint：`/v1/images/generations`；Header：`Authorization: Bearer <key>`、`Content-Type: application/json`、`X-ModelScope-Async-Mode: true`。
- Payload：`{"model", "prompt", "size", "negative_prompt", "seed"}`；`size` 是字符串 `WxH`。
- 尺寸：默认直接用输出分辨率（如 `1080x1920` / `1920x1080`）。Z-Image 支持总像素 `512*512`–`2048*2048`；实测 `1920x1080` 可用。超过 2048 或总像素上限时自动降采样到最长边 2048，合成时再放大。
- 输出统一转 JPEG（`-q:v 2`），保留 `.png` 兼容旧项目；不再默认生成大体积 PNG。
- 返回 `task_id` → 轮询 `/v1/tasks/{task_id}`（header `X-ModelScope-Task-Type: image_generation`），`task_status=SUCCEED` 后下载 `output_images[0]`。
- 轮询间隔 15 秒；单任务 600 秒超时；并发 3–4；失败换下一个 profile。
- 提示词用英文；negative 固定：`text, watermark, logo, split screen, collage, deformed hands, extra fingers, oversaturated`。

本地备选：`mflux` + FLUX.2 Klein 4B，输出 `720x1280` / `1280x720`，合成时放大到 1080p。

## 合成

只用 ffmpeg（系统已装 8.0.1）。参数见 `ffmpeg.md`。

## 环境变量

```bash
VCS_ASR_MODEL=mlx-community/Qwen3-ASR-1.7B-8bit
VCS_TTS_MODEL=mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16
VCS_IMAGE_PROVIDER=modelscope  # modelscope | mock
VCS_MODELSCOPE_API_KEY=        # 单 Key（向后兼容）
VCS_MODELSCOPE_CN_KEY=         # providers.json 多账号
VCS_MODELSCOPE_INTL_KEY=       # 国际站
VCS_LLM_1_KEY=                  # 文本 API 1
VCS_LLM_2_KEY=                  # 文本 API 2
```
