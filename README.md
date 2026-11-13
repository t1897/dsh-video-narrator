# Video Narrator for DeepSeek Harness

[English](README.md) | [中文](README.zh.md)

A DSH skill that turns a video, video URL, article URL, PDF, or plain text into a narrated video: cleaned transcript, segmented narration script, title and 10 tags, per-scene image prompts, generated images, TTS audio, and a final MP4 assembled with ffmpeg.

![Output overview](assets/screenshot-1.png)

## What it does

1. Ingests local video/audio, YouTube/Bilibili URLs, article URLs, PDFs, or text.
2. Transcribes video with Qwen3-ASR (MLX).
3. Cleans the source into Markdown, then writes a timed narration script.
4. Generates a title, description, and exactly 10 tags for `04_metadata.json`.
5. Writes orientation-aware image prompts and generates one image per scene through ModelScope.
6. Generates one TTS clip per scene with Qwen3-TTS (MLX), fixed seed and optional reference audio.
7. Composes scene clips with ffmpeg, concatenates them, names the result from `metadata.title`, and removes intermediates.

## Requirements

- macOS on Apple Silicon for the local MLX stages (ASR and TTS).
- `ffmpeg` and `ffprobe` on `PATH`.
- `yt-dlp` for video URLs.
- Python 3.12/3.13 with `pypdf` and `trafilatura` for ingestion.
- Python 3.12/3.13 with `mlx-audio` and `mlx-qwen3-asr` for ASR/TTS.
- A ModelScope API token for image generation. Domestic and international endpoints are both supported.

## Install

Install from the DSH plugin market, or use **Plugins → Add plugin** with this repository. The bundle registers the `video-narrator` skill; no separate skill copy is needed.

## Configure

Copy the environment template and fill only the keys you use:

```bash
cp .env.example .env
```

For multiple text or image accounts, copy `providers.example.json` to `providers.json` and edit the ordered profiles:

```bash
cp providers.example.json providers.json
python3 scripts/vcs.py providers --file providers.json
```

`providers.json` is gitignored. Keys are read from environment variables named by `api_key_env`. The `text` array is tried in order by `vcs text`; the `image` array is tried in order per scene. ModelScope domestic (`api-inference.modelscope.cn`) and international (`api-inference.modelscope.ai`) endpoints can be mixed.

## Use

Ask the agent for a video from a URL, PDF, article, or text. The skill asks for orientation, duration (fixed, range, or unlimited), segment length, voice, and style before generating.

The CLI is also usable directly:

```bash
# ingest
python3 scripts/vcs.py ingest --input "https://www.youtube.com/watch?v=..." --orientation portrait --duration 5-8

# transcribe video input
HF_HOME="$HOME/.cache/vcs/hf" python3 scripts/vcs.py asr --project <project> --language English

# Agent writes transcript.md / script.json / metadata.json / image_prompts.json, then:
python3 scripts/vcs.py validate --project <project>

# media
python3 scripts/vcs.py images --project <project>
HF_HOME="$HOME/.cache/vcs/hf" python3 scripts/vcs.py tts --project <project>
python3 scripts/vcs.py compose --project <project>
```

## Output

```text
projects/
└── YouTube_11122026_<metadata title>/
    ├── 01_transcript.raw.txt
    ├── 02_transcript.md
    ├── 03_script.json
    ├── 04_metadata.json
    ├── 05_image_prompts.json
    ├── 06_images/
    ├── 07_<metadata title>.mp4
    └── source/<original>.pdf   # PDF input only
```

Audio, scene clips, logs, and temporary files are removed after `compose` by default; pass `--keep-intermediates` to keep them. `04_metadata.json` records the source type, platform or domain, original URL, syndicated URL, or copied PDF path.

## Notes and limits

- v1 does not generate subtitles.
- Image generation needs a ModelScope token; it is not bundled.
- No voice sample is bundled. TTS uses the model's default voice, or pass `--voice-ref` with audio you have the right to use.
- Paywall circumvention is not implemented. For restricted articles, use an authorized copy, a free syndicated copy, or saved HTML via `vcs ingest --html`.
- Local model sizes: ASR about 2.3 GB and TTS about 4.5 GB on first use; image generation runs remotely.
- The compose step requires the same codec/fps/audio parameters across all scene clips; the included script enforces this.

## License

MIT. See [LICENSE](LICENSE).
