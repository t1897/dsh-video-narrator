# Video Narrator for DeepSeek Harness（中文）

一个 DSH Skill：把视频、视频链接、文章链接、PDF 或纯文本，转成带配图与配音的口播视频。产出包括清洗后的文稿、分段口播稿、标题与 10 个标签、每段配图 Prompt、场景图片、TTS 音频，以及用 ffmpeg 合成的最终 MP4。

![成片预览](assets/screenshot-1.png)

## 功能

1. 接收本地视频/音频、YouTube/Bilibili 链接、文章链接、PDF 或文本。
2. 视频用 Qwen3-ASR（MLX）转写。
3. 把素材整理成 Markdown 文稿，再写成带时长控制的口播稿。
4. 生成有吸引力的标题、简介和恰好 10 个 tags，写入 `04_metadata.json`。
5. 按横屏/竖屏生成构图不同的配图 Prompt，并通过魔搭 ModelScope 逐段生图。
6. 用 Qwen3-TTS（MLX）逐段配音；固定 seed，参考音必需。
7. 用 ffmpeg 逐段合成、concat 合并，按 `metadata.title` 命名，并清理中间文件。

## 环境要求

- Apple Silicon macOS（本地 MLX 的 ASR/TTS 需要）。
- `ffmpeg`、`ffprobe` 在 `PATH` 中。
- `yt-dlp`（视频链接需要）。
- Python 3.12/3.13 + `pypdf`、`trafilatura`（用于采集）。
- Python 3.12/3.13 + `mlx-audio`、`mlx-qwen3-asr`（用于 ASR/TTS）。
- 魔搭 ModelScope API Token（生图需要）；国内站和国际站都支持。

## 安装

从 DSH 插件市场安装，或在 **Plugins → Add plugin** 里添加本仓库。bundle 会自动注册 `video-narrator` Skill，不需要再单独复制 Skill。

## 配置

```bash
cp .env.example .env
```

如果有多套文本或生图账号，复制 `providers.example.json` 为 `providers.json`，按顺序编辑 profile：

```bash
cp providers.example.json providers.json
python3 scripts/vcs.py providers --file providers.json
```

`providers.json` 已被 gitignore。Key 通过 `api_key_env` 指向 `.env` 里的环境变量。`text` 数组由 `vcs text` 按顺序回退；`image` 数组按场景顺序回退。魔搭国内站（`api-inference.modelscope.cn`）和国际站（`api-inference.modelscope.ai`）可以混排。

## 控制 UI

安装后，左侧边栏会出现 **视频** 入口。点开是常驻主面板工作台：左侧列出 `runs/` 和 `projects/` 里的历史项目（标题、状态、画幅、时长、图片数），右侧设置下一条视频（素材、画幅、时长、每段秒数、音色、风格）。点 **开始生成** 会新建会话并带上结构化请求。消息带有 `[VCS_PARAMS_CONFIRMED]`，Skill 不会再次询问同一批参数。

## 使用

直接对 Agent 说要做一条口播视频即可。Skill 会**先弹出参数确认对话框**，确认画幅、时长（固定/范围/不限）、每段秒数、音色和风格后才开始生成。

也可以直接用 CLI：

```bash
# 采集
python3 scripts/vcs.py ingest --input "https://www.youtube.com/watch?v=..." --orientation portrait --duration 5-8

# 视频输入需要转写
HF_HOME="$HOME/.cache/vcs/hf" python3 scripts/vcs.py asr --project <项目目录> --language English

# Agent 写入 02_transcript.md / 03_script.json / 04_metadata.json / 05_image_prompts.json 后校验
python3 scripts/vcs.py validate --project <项目目录>

# 媒体生成
python3 scripts/vcs.py images --project <项目目录>
HF_HOME="$HOME/.cache/vcs/hf" python3 scripts/vcs.py tts --project <项目目录>
python3 scripts/vcs.py compose --project <项目目录>
```

## 输出目录

```text
projects/
└── YouTube_11122026_<metadata 标题>/
    ├── 01_transcript.raw.txt
    ├── 02_transcript.md
    ├── 03_script.json
    ├── 04_metadata.json
    ├── 05_image_prompts.json
    ├── 06_images/
    ├── 07_<metadata 标题>.mp4
    └── source/<原文件>.pdf   # 仅 PDF 输入保留
```

`compose` 完成后默认删除 `audio/`、`clips/`、`logs/` 和临时文件；加 `--keep-intermediates` 可保留。`04_metadata.json` 会记录来源类型、平台或域名、原始 URL、转载 URL，或 PDF 文件路径。

## 注意与限制

- v1 不生成字幕。
- 生图需要自己的 ModelScope Token，不随插件分发。
- 内置两个参考音：`assets/voice_female.mp3` 和 `assets/voice_male.mp3`。TTS 始终要求参考音；换音色用 `--voice-ref` + `--voice-ref-text`。参考音不适用 MIT 许可，见 [assets/VOICE-LICENSE.md](assets/VOICE-LICENSE.md)。
- 不实现付费墙绕过。受限文章请使用授权副本、免费转载副本，或用 `vcs ingest --html` 导入已保存页面。
- 本地模型首次使用需下载：ASR 约 2.3GB，TTS 约 4.5GB；生图在云端运行。
- 合成要求所有分段使用相同的编码/帧率/音频参数，脚本已统一处理。

## 许可

MIT，见 [LICENSE](LICENSE)。
