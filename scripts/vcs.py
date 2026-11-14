#!/usr/bin/env python3
"""vcs - video creation skill CLI.

M0 scope: project scaffolding, mock text/image/tts providers, and the real
ffmpeg compose/finalize path.  Real ASR/LLM/ModelScope providers are added in
M1-M3; the state/file contract is already fixed here so those providers can be
dropped in without changing the CLI.

Usage:
    python3 vcs.py doctor
    python3 vcs.py run --mock --minutes 1 --orientation portrait
    python3 vcs.py status [PROJECT]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

VERSION = "0.1.0"
SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_PARENT = Path.cwd() / "projects"

DEFAULTS: dict[str, Any] = {
    "minutes": 6.0,
    "segment_seconds": [20, 40],
    "target_segment_seconds": 30,
    "orientation": "portrait",
    "fps": 30,
    "voice": "female",
    "style": "cinematic",
    "language": "zh",
    "chars_per_second": 5.1,
    "asr_model": "mlx-community/Qwen3-ASR-1.7B-8bit",
    "image_model": "Tongyi-MAI/Z-Image-Turbo",
}

COLORS = [
    ("0x16222e", "0x8a5a2b"),
    ("0x1c2b22", "0x7a6a3a"),
    ("0x241b2f", "0x6a4a7a"),
    ("0x2b1e1e", "0x9a5a4a"),
    ("0x1a2630", "0x4a7a8a"),
]


class VcsError(RuntimeError):
    """User-facing error with a clean message."""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def eprint(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def run(cmd: list[str], timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise VcsError(f"command not found: {cmd[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise VcsError(f"command timed out: {' '.join(cmd)}") from exc
    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or proc.stdout or "").strip().splitlines()[-12:])
        raise VcsError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{tail}")
    return proc


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VcsError(f"cannot read JSON: {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def ffprobe_duration(path: Path) -> float:
    proc = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path),
    ])
    try:
        return float(proc.stdout.strip())
    except ValueError as exc:
        raise VcsError(f"cannot read duration: {path}") from exc


def ffprobe_size(path: Path) -> tuple[int, int]:
    proc = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path),
    ])
    try:
        width, height = proc.stdout.strip().split("x")
        return int(width), int(height)
    except ValueError as exc:
        raise VcsError(f"cannot read image size: {path}") from exc


def slugify(text: str, limit: int = 40) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip(), flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:limit] or "project"


def safe_filename(title: str, limit: int = 120) -> str:
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "", title or "").strip().strip(".")
    name = re.sub(r"\s+", " ", name)
    return (name[:limit].strip() or "video")


def human_size(bytes_count: int) -> str:
    value = float(bytes_count)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}GB"


def default_hf_home() -> Path:
    return Path(os.environ.get("VCS_HF_HOME") or (Path.home() / ".cache" / "vcs" / "hf"))


def load_env_files() -> None:
    """Load .env without overriding variables already set in the shell."""
    candidates = [
        Path.cwd() / ".env",
        SKILL_ROOT / ".env",
        SKILL_ROOT.parent / ".env",
        Path.home() / ".vcs.env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


# ---------------------------------------------------------------------------
# providers: ordered fallback profiles
# ---------------------------------------------------------------------------

def _default_providers() -> dict[str, Any]:
    return {
        "text": [{"name": "agent", "provider": "agent"}],
        "image": [{
            "name": "modelscope-env",
            "provider": "modelscope",
            "base_url": os.environ.get("VCS_MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn"),
            "api_key_env": "VCS_MODELSCOPE_API_KEY",
            "model": os.environ.get("VCS_MODELSCOPE_IMAGE_MODEL", DEFAULTS["image_model"]),
        }],
    }


def load_providers(path: str | None = None, project_root: Path | None = None) -> dict[str, Any]:
    candidates: list[Path] = []
    if path:
        candidates.append(Path(path).expanduser())
    if os.environ.get("VCS_PROVIDERS_FILE"):
        candidates.append(Path(os.environ["VCS_PROVIDERS_FILE"]).expanduser())
    if project_root:
        candidates.append(Path(project_root) / "providers.json")
    candidates += [Path.cwd() / "providers.json", SKILL_ROOT / "providers.json", Path.home() / ".config" / "vcs" / "providers.json"]
    for candidate in candidates:
        if candidate.exists():
            data = load_json(candidate)
            if isinstance(data, dict):
                data.setdefault("text", [])
                data.setdefault("image", [])
                return data
    return _default_providers()


def resolve_api_key(profile: dict[str, Any]) -> str:
    if profile.get("api_key"):
        return str(profile["api_key"]).strip()
    env_name = str(profile.get("api_key_env") or "").strip()
    return os.environ.get(env_name, "").strip() if env_name else ""


def _chat_url(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def call_text_api(profile: dict[str, Any], prompt: str, *, json_mode: bool = False) -> str:
    name = profile.get("name") or "text"
    base = str(profile.get("base_url") or "").strip()
    model = str(profile.get("model") or "").strip()
    key = resolve_api_key(profile)
    if not base or not model:
        raise VcsError(f"text profile {name}: base_url and model are required")
    if not key:
        raise VcsError(f"text profile {name}: missing API key (set {profile.get('api_key_env') or 'api_key'})")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": float(profile.get("temperature", 0.7)),
    }
    if json_mode or profile.get("json_mode"):
        payload["response_format"] = {"type": "json_object"}
    timeout = int(os.environ.get("VCS_TEXT_TIMEOUT_SEC", "180"))
    try:
        data = _http_json(
            _chat_url(base), payload,
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=timeout,
        )
    except VcsError as exc:
        if json_mode and ("HTTP 400" in str(exc) or "HTTP 422" in str(exc)):
            payload.pop("response_format", None)
            data = _http_json(
                _chat_url(base), payload,
                {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                timeout=timeout,
            )
        else:
            raise
    choices = data.get("choices") or []
    if not choices:
        raise VcsError(f"text profile {name}: no choices in response")
    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content)
    text = str(content).strip()
    if not text:
        raise VcsError(f"text profile {name}: empty response")
    return text


def text_profiles(providers: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in providers.get("text", []) if p.get("provider") in {"openai", "http", "openai_compatible"}]


def image_profiles(providers: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in providers.get("image", []) if p.get("provider") in {"modelscope", "openai", "http", "openai_compatible"}]


def parse_json_response(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(raw[start:end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    raise VcsError(f"response is not valid JSON: {raw[:300]}")


# ---------------------------------------------------------------------------
# project
# ---------------------------------------------------------------------------

class Project:
    def __init__(self, root: Path, config: dict[str, Any]):
        self.root = root
        self.config = config

    # paths
    def p(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    @property
    def state_path(self) -> Path:
        return self.p("state.json")

    def state(self) -> dict[str, Any]:
        return load_json(self.state_path, {"version": 1, "stages": {}}) or {"version": 1, "stages": {}}

    def mark(self, stage: str, outputs: list[Path], **extra: Any) -> None:
        state = self.state()
        state.setdefault("stages", {})[stage] = {
            "status": "done",
            "updated_at": now_iso(),
            "outputs": [str(path.relative_to(self.root)) for path in outputs],
            **extra,
        }
        write_json(self.state_path, state)

    def stage_done(self, stage: str) -> bool:
        row = self.state().get("stages", {}).get(stage, {})
        if row.get("status") != "done":
            return False
        return all((self.root / rel).exists() for rel in row.get("outputs", []))

    def save(self) -> None:
        write_json(self.p("project.json"), self.config)

    @classmethod
    def create(cls, root: Path, config: dict[str, Any]) -> "Project":
        root.mkdir(parents=True, exist_ok=True)
        for folder in ("source", "06_images", "audio", "clips", "logs"):
            (root / folder).mkdir(parents=True, exist_ok=True)
        project = cls(root, config)
        project.save()
        write_json(project.state_path, {"version": 1, "stages": {}})
        return project

    @classmethod
    def load(cls, root: Path) -> "Project":
        config = load_json(root / "project.json")
        if not isinstance(config, dict):
            raise VcsError(f"not a vcs project: {root}")
        return cls(root, config)


def _parse_duration(args: argparse.Namespace) -> tuple[str, float | None, float | None]:
    if getattr(args, "unlimited", False):
        return "unlimited", None, None
    raw = getattr(args, "duration", None)
    if raw:
        value = str(raw).strip().lower()
        if value in {"unlimited", "none", "no-limit", "nolimit", "不限"}:
            return "unlimited", None, None
        if "-" in value:
            left, right = [part.strip() for part in value.split("-", 1)]
            try:
                low, high = float(left), float(right)
            except ValueError as exc:
                raise VcsError(f"invalid duration range: {raw!r} (use e.g. 5-8)") from exc
            if low <= 0 or high <= 0 or low > high:
                raise VcsError(f"invalid duration range: {raw!r}")
            return "range", low, high
        try:
            minutes = float(value)
        except ValueError as exc:
            raise VcsError(f"invalid duration: {raw!r} (use 6, 5-8, or unlimited)") from exc
        if minutes <= 0:
            raise VcsError("duration must be positive")
        return "fixed", minutes, minutes
    if getattr(args, "minutes", None) is not None:
        minutes = float(args.minutes)
        if minutes <= 0:
            raise VcsError("--minutes must be positive")
        return "fixed", minutes, minutes
    minutes = float(DEFAULTS["minutes"])
    return "fixed", minutes, minutes


def _parse_segment_range(args: argparse.Namespace) -> tuple[int, int, int]:
    raw = str(getattr(args, "segment_range", None) or "20-40").strip()
    if "-" not in raw:
        raise VcsError(f"invalid segment range: {raw!r} (use e.g. 20-40)")
    left, right = [part.strip() for part in raw.split("-", 1)]
    try:
        low, high = int(left), int(right)
    except ValueError as exc:
        raise VcsError(f"invalid segment range: {raw!r}") from exc
    if low <= 0 or high <= 0 or low > high:
        raise VcsError(f"invalid segment range: {raw!r}")
    target = int(getattr(args, "segment", None) or round((low + high) / 2))
    target = max(low, min(high, target))
    return low, high, target


def _domain_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for prefix in ("www.", "m.", "amp."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    parts = host.split(".")
    if len(parts) >= 3:
        two_level = ".".join(parts[-2:])
        if two_level in {"com.sg", "com.cn", "com.hk", "com.tw", "com.my", "com.au", "com.br",
                         "co.uk", "co.jp", "co.nz", "co.in", "co.za", "com.mx"}:
            return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _platform_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if "youtube" in host or "youtu.be" in host:
        return "YouTube"
    if "bilibili" in host or "b23.tv" in host:
        return "Bilibili"
    if "vimeo" in host:
        return "Vimeo"
    if "twitter" in host or host == "x.com" or host.endswith(".x.com"):
        return "X"
    return "Video"


def _source_label(input_path: str | None, input_type: str, mock: bool) -> str:
    if not input_path:
        return "Mock" if mock else "Text"
    if input_type == "pdf":
        return "PDF"
    if input_type == "article":
        return _domain_of(input_path) or "Web"
    if input_type == "video":
        if input_path.startswith(("http://", "https://")):
            return _platform_of(input_path)
        return "Video"
    return "Text"


def image_size_for(width: int, height: int) -> str:
    """Pick a Z-Image-compatible size that matches the output aspect.

    Z-Image accepts 512*512 through 2048*2048 total pixels.  For common
    1080p/720p outputs we pass the exact frame size; larger/custom frames are
    scaled down to the model's max edge and then upscaled by ffmpeg at compose.
    """
    w, h = max(1, int(width)), max(1, int(height))
    total = w * h
    min_total = 512 * 512
    max_total = 2048 * 2048
    if total < min_total:
        scale = (min_total / total) ** 0.5
        w, h = int(w * scale), int(h * scale)
        total = w * h
    if total > max_total or max(w, h) > 2048:
        scale = min(1.0, 2048 / max(w, h), (max_total / total) ** 0.5)
        w, h = int(w * scale), int(h * scale)
    w = max(2, w // 2 * 2)
    h = max(2, h // 2 * 2)
    return f"{w}x{h}"


def scene_image_path(project: "Project", scene_id: int) -> Path:
    """Return the existing scene image, preferring JPEG over legacy PNG."""
    image_dir = project.p("06_images")
    for suffix in (".jpg", ".jpeg", ".png"):
        path = image_dir / f"scene_{scene_id:03d}{suffix}"
        if path.exists():
            return path
    return image_dir / f"scene_{scene_id:03d}.jpg"


def build_config(args: argparse.Namespace, *, input_path: str | None, mock: bool) -> dict[str, Any]:
    mode, duration_min, duration_max = _parse_duration(args)
    if mode == "fixed":
        minutes = float(duration_min or DEFAULTS["minutes"])
    elif mode == "range":
        minutes = round((float(duration_min) + float(duration_max)) / 2, 2)
    else:
        minutes = 0.0
    seg_min, seg_max, target_segment = _parse_segment_range(args)

    orientation = args.orientation
    custom_width = int(getattr(args, "width", 0) or 0)
    custom_height = int(getattr(args, "height", 0) or 0)
    if custom_width > 0 and custom_height > 0:
        width, height = custom_width, custom_height
    elif orientation == "portrait":
        width, height = 1080, 1920
    else:
        width, height = 1920, 1080
    image_size = image_size_for(width, height)

    config = {
        "version": 1,
        "created_at": now_iso(),
        "input": input_path or "",
        "mock": mock,
        "input_type": _detect_input_type(input_path, "auto") if input_path else "text",
        "source_label": _source_label(input_path, _detect_input_type(input_path, "auto") if input_path else "text", mock),
        "source_platform": _platform_of(input_path) if input_path and _detect_input_type(input_path, "auto") == "video" and input_path.startswith(("http://", "https://")) else ("Video" if input_path and _detect_input_type(input_path, "auto") == "video" else ""),
        "source_domain": _domain_of(input_path) if input_path and _detect_input_type(input_path, "auto") == "article" else "",
        "source_url": input_path if input_path and input_path.startswith(("http://", "https://")) else "",
        "source_file": "",
        "folder_date": datetime.now().strftime("%m%d%Y"),
        "folder_base": "",
        "folder_name": "",
        "folder_title": "",
        "auto_folder_name": not bool(getattr(args, "out", None)),
        "duration_mode": mode,
        "duration_min": duration_min,
        "duration_max": duration_max,
        "minutes": minutes,
        "max_segments": 60,
        "segment_seconds": [seg_min, seg_max],
        "target_segment_seconds": target_segment,
        "orientation": orientation,
        "width": width,
        "height": height,
        "fps": int(args.fps),
        "voice": args.voice,
        "style": args.style,
        "language": args.language,
        "chars_per_second": float(args.chars_per_second),
        "image_size": image_size,
        "providers": {
            "text": "agent" if not mock else "mock",
            "image": "modelscope" if not mock else "mock",
            "tts": "local" if not mock else "mock",
        },
        "models": {
            "asr": "mlx-community/Qwen3-ASR-1.7B-8bit",
            "tts": "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16",
            "image": "Tongyi-MAI/Z-Image-Turbo",
        },
        "ffmpeg": {
            "preset": "veryfast",
            "crf": 20,
            "gop": int(args.fps) * 2,
            "audio_bitrate": "128k",
        },
    }
    config["folder_base"] = f"{config['source_label']}_{config['folder_date']}"
    config["folder_name"] = config["folder_base"]
    return config

# ---------------------------------------------------------------------------
# mock providers
# ---------------------------------------------------------------------------

SENTENCES = [
    "很多人以为短视频最难的是拍摄，其实真正耗时的是把文字变成画面。",
    "先把素材整理成一份干净的文稿，再决定这一条视频到底要讲哪一件事。",
    "口播稿要像说话，不要像写论文，句子短一点，信息密度反而更高。",
    "每一段只讲一个意思，观众才不会在三十秒里丢失重点。",
    "画面不需要很复杂，一个主体、一层背景、干净的光线就足够。",
    "声音是口播视频的灵魂，音色稳定比偶尔一句好听更重要。",
    "最后把所有片段接起来，检查一遍总时长和结尾有没有被截断。",
]

ORIENTATION_HINT = {
    "portrait": "9:16 vertical composition, medium close-up, subject in the upper-middle, bottom 30% clean for captions",
    "landscape": "16:9 horizontal composition, medium-wide shot, subject on the left third, clean negative space on the right",
}


def mock_script(config: dict[str, Any]) -> dict[str, Any]:
    mode = str(config.get("duration_mode") or "fixed")
    minutes = float(config.get("minutes") or 3.0)
    target = int(config["target_segment_seconds"])
    count = max(2, min(30, round(minutes * 60 / max(1, target)))) if mode != "unlimited" else 6
    cps = float(config["chars_per_second"])
    segments = []
    for index in range(1, count + 1):
        target_chars = max(60, int(target * cps))
        text = f"第{index}段。"
        cursor = 0
        while len(text) < target_chars:
            text += SENTENCES[cursor % len(SENTENCES)]
            cursor += 1
        narration = text[:target_chars].rstrip("，。") + "。"
        segments.append({
            "id": index,
            "narration": narration,
            "est_seconds": round(len(narration) / cps, 1),
        })
    if mode == "unlimited":
        duration_label = "不限时长"
    elif mode == "range":
        duration_label = f"{float(config.get('duration_min')):g}–{float(config.get('duration_max')):g} 分钟"
    else:
        duration_label = f"{minutes:g} 分钟"
    return {
        "title": f"测试视频：{duration_label}{'竖屏' if config['orientation'] == 'portrait' else '横屏'}口播",
        "language": config["language"],
        "duration_mode": mode,
        "target_seconds": 0 if mode == "unlimited" else int(minutes * 60),
        "segment_seconds": config["segment_seconds"],
        "segments": segments,
    }


def mock_metadata(script: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": script["title"],
        "description": "这是一条用于验证视频生成流水线的测试视频，覆盖文稿、分段、配图、配音与合成。",
        "tags": ["口播视频", "短视频", "AI配音", "自动配图", "视频制作",
                 "内容创作", "效率工具", "横屏竖屏", "工作流", "测试"],
    }


def mock_image_prompts(script: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    hint = ORIENTATION_HINT[config["orientation"]]
    scenes = []
    for segment in script["segments"]:
        scenes.append({
            "id": segment["id"],
            "prompt": (
                f"Cinematic still, scene {segment['id']}, a calm workspace with soft window light, "
                f"muted teal and warm amber palette, shallow depth of field, {hint}, "
                "one single frame, no text, no watermark, no logo"
            ),
            "seed": 1000 + segment["id"],
        })
    return {
        "version": 1,
        "orientation": config["orientation"],
        "style": config["style"],
        "negative": "text, watermark, logo, split screen, collage, deformed hands, extra fingers, oversaturated",
        "scenes": scenes,
    }


def mock_image(path: Path, width: int, height: int, index: int) -> None:
    c0, c1 = COLORS[(index - 1) % len(COLORS)]
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi",
        "-i", f"gradients=s={width}x{height}:c0={c0}:c1={c1}:x0=0:y0=0:x1={width}:y1={height}:d=1",
        "-frames:v", "1", str(path),
    ])
    if not path.exists() or path.stat().st_size < 1024:
        raise VcsError(f"mock image was not created: {path}")
    actual = ffprobe_size(path)
    if actual != (width, height):
        raise VcsError(f"mock image has wrong size {actual}, expected {(width, height)}")


def mock_audio(path: Path, duration: float, sample_rate: int = 24000) -> None:
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"anullsrc=r={sample_rate}:cl=mono",
        "-t", f"{duration:.3f}", "-c:a", "pcm_s16le", str(path),
    ])
    if not path.exists() or path.stat().st_size < 1024:
        raise VcsError(f"mock audio was not created: {path}")


# ---------------------------------------------------------------------------
# M1: ingest + ASR
# ---------------------------------------------------------------------------

VIDEO_HOSTS = ("youtube.com", "youtu.be", "bilibili.com", "b23.tv", "vimeo.com", "twitter.com", "x.com")


def _http_get(url: str, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as exc:
        raise VcsError(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise VcsError(f"network error for {url}: {exc.reason}") from exc


def _extract_article(url: str, html_path: str | None = None) -> tuple[str, str]:
    import trafilatura

    html = Path(html_path).read_text(encoding="utf-8", errors="ignore") if html_path else _http_get(url)
    text = trafilatura.extract(
        html, include_comments=False, include_tables=False, favor_recall=True
    ) or ""
    text = text.strip()
    if len(text) < 500:
        raise VcsError(
            f"article extraction too short ({len(text)} chars). "
            "The site may block automated readers. Save the page HTML and pass --html, "
            "or use a free syndicated copy of the article."
        )
    return text, html


def _detect_input_type(raw: str, explicit: str) -> str:
    if explicit != "auto":
        return explicit
    if raw.startswith(("http://", "https://")):
        host = raw.split("/")[2].lower()
        return "video" if any(h in host for h in VIDEO_HOSTS) else "article"
    suffix = Path(raw).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".mp4", ".mov", ".mkv", ".webm", ".m4a", ".mp3", ".wav", ".aac", ".flac"}:
        return "video"
    return "text"


def ingest_project(project: Project, args: argparse.Namespace) -> None:
    raw = args.input
    input_type = _detect_input_type(raw, args.type)
    source_dir = project.p("source")
    source_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, Any] = {"input": raw, "type": input_type, "fetched_at": now_iso()}
    raw_text = ""

    if input_type == "video":
        if raw.startswith(("http://", "https://")):
            info_raw = run([
                "yt-dlp", "--skip-download", "--dump-single-json", "--no-playlist", "--no-warnings", raw,
            ]).stdout
            info = json.loads(info_raw)
            meta.update({
                "title": info.get("title"),
                "duration": info.get("duration"),
                "webpage_url": info.get("webpage_url"),
                "uploader": info.get("uploader"),
                "id": info.get("id"),
            })
            template = str(source_dir / "source.%(ext)s")
            run([
                "yt-dlp", "-x", "--audio-format", "wav", "--audio-quality", "0",
                "--no-playlist", "--no-warnings", "-o", template, raw,
            ])
        else:
            src = Path(raw).expanduser()
            if not src.exists():
                raise VcsError(f"input not found: {src}")
            shutil.copy2(src, source_dir / src.name)
            meta.update({"title": src.stem, "filename": src.name})
        wavs = sorted(source_dir.glob("source*.wav"))
        if not wavs:
            raise VcsError("video download produced no WAV file")
        wav = wavs[0]
        if wav.name != "source.wav":
            wav.replace(source_dir / "source.wav")
    elif input_type == "article":
        text, html = _extract_article(raw, getattr(args, "html", None))
        raw_text = text
        meta.update({"title": _guess_title(html) or raw, "url": raw})
        (source_dir / "source.html").write_text(html, encoding="utf-8")
    elif input_type == "pdf":
        try:
            from pypdf import PdfReader
        except ModuleNotFoundError as exc:
            raise VcsError("pypdf is required for PDF input; run with the project .venv") from exc
        src = Path(raw).expanduser()
        if not src.exists():
            raise VcsError(f"input not found: {src}")
        shutil.copy2(src, source_dir / src.name)
        reader = PdfReader(str(src))
        raw_text = "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
        if len(raw_text) < 500:
            raise VcsError("PDF text extraction too short; it may be a scanned PDF (OCR needed)")
        meta.update({"title": src.stem, "filename": src.name, "pages": len(reader.pages)})
    elif input_type == "text":
        src = Path(raw).expanduser()
        if not src.exists():
            raise VcsError(f"input not found: {src}")
        shutil.copy2(src, source_dir / src.name)
        raw_text = src.read_text(encoding="utf-8", errors="ignore")
        meta.update({"title": src.stem, "filename": src.name})
    else:
        raise VcsError(f"unsupported input type: {input_type}")

    if raw_text:
        project.p("01_transcript.raw.txt").write_text(raw_text, encoding="utf-8")
        meta["chars"] = len(raw_text)
    write_json(source_dir / "source.json", meta)
    platform = _platform_of(raw) if input_type == "video" and raw.startswith(("http://", "https://")) else ("Video" if input_type == "video" else "")
    domain = _domain_of(raw) if input_type == "article" else ""
    source_file = f"source/{meta.get('filename')}" if input_type == "pdf" and meta.get("filename") else ""
    project.config.update({
        "input": raw,
        "input_type": input_type,
        "source_title": meta.get("title") or Path(raw).stem,
        "source_label": _source_label(raw, input_type, False),
        "source_platform": platform,
        "source_domain": domain,
        "source_url": meta.get("webpage_url") or meta.get("url") or (raw if raw.startswith(("http://", "https://")) else ""),
        "source_file": source_file,
    })
    if not project.config.get("folder_base"):
        project.config["folder_base"] = f"{project.config['source_label']}_{project.config.get('folder_date') or datetime.now().strftime('%m%d%Y')}"
        project.config["folder_name"] = project.config["folder_base"]
    project.save()
    project.mark("ingest", [source_dir / "source.json"], input_type=input_type)
    eprint(f"ingest: {input_type} -> {meta.get('title')}")


def _guess_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def transcribe_project(project: Project, *, language: str = "English", model: str | None = None) -> None:
    wav = project.p("source", "source.wav")
    if not wav.exists():
        raise VcsError(f"missing source audio: {wav}")
    model_id = model or project.config.get("models", {}).get("asr") or DEFAULTS["asr_model"]
    chunk_dir = project.p("source", "chunks")
    chunk_dir.mkdir(parents=True, exist_ok=True)
    for old in chunk_dir.glob("chunk_*.wav"):
        old.unlink()
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav),
        "-f", "segment", "-segment_time", "30", "-ac", "1", "-ar", "16000",
        str(chunk_dir / "chunk_%03d.wav"),
    ])
    chunks = sorted(chunk_dir.glob("chunk_*.wav"))
    if not chunks:
        raise VcsError("audio chunking produced no files")
    os.environ.setdefault("HF_HOME", str(default_hf_home()))
    from mlx_audio.stt import load as load_stt

    eprint(f"asr: loading {model_id}")
    stt = load_stt(model_id)
    texts: list[str] = []
    for index, chunk in enumerate(chunks, 1):
        eprint(f"asr: chunk {index}/{len(chunks)}")
        result = stt.generate(str(chunk), language=language)
        text = getattr(result, "text", str(result)).strip()
        if text:
            texts.append(text)
    raw = "\n\n".join(texts).strip()
    project.p("01_transcript.raw.txt").write_text(raw + "\n", encoding="utf-8")
    project.mark("asr", [project.p("01_transcript.raw.txt")], model=model_id, language=language, chunks=len(chunks))
    eprint(f"asr: {len(raw)} chars")


def cmd_ingest(args: argparse.Namespace) -> int:
    project = Project.load(Path(args.project).expanduser()) if args.project else create_project(args, mock=False)
    ingest_project(project, args)
    print(project.root)
    return 0


def cmd_asr(args: argparse.Namespace) -> int:
    project = Project.load(Path(args.project).expanduser()) if args.project else latest_project()
    if project is None:
        raise VcsError("no project found; pass --project")
    transcribe_project(project, language=args.language, model=args.model or None)
    print(project.root)
    return 0


# ---------------------------------------------------------------------------
# M2: validation of agent-written text files
# ---------------------------------------------------------------------------

def source_info(project: Project) -> dict[str, Any]:
    cfg = project.config
    input_value = str(cfg.get("input") or "")
    input_type = str(cfg.get("input_type") or ("pdf" if input_value.lower().endswith(".pdf") else "text"))
    label = str(cfg.get("source_label") or _source_label(input_value or None, input_type, bool(cfg.get("mock"))))
    platform = str(cfg.get("source_platform") or "")
    domain = str(cfg.get("source_domain") or "")
    if input_type == "video" and not platform:
        platform = _platform_of(input_value) if input_value.startswith(("http://", "https://")) else "Video"
    if input_type == "article" and not domain:
        domain = _domain_of(input_value)
    url = str(cfg.get("source_url") or "")
    if not url and input_value.startswith(("http://", "https://")):
        url = input_value
    file_value = str(cfg.get("source_file") or "")
    if not file_value and input_type == "pdf":
        pdfs = sorted(project.p("source").glob("*.pdf"))
        if pdfs:
            file_value = f"source/{pdfs[0].name}"
    info = {
        "type": input_type,
        "label": label,
        "platform": platform,
        "domain": domain,
        "url": url,
        "file": file_value,
        "syndicated_url": str(cfg.get("syndicated_url") or ""),
    }
    return {key: value for key, value in info.items() if value}


def attach_source(project: Project, metadata: dict[str, Any]) -> dict[str, Any]:
    metadata["source"] = source_info(project)
    return metadata


def maybe_rename_project_folder(project: Project, title: str | None = None) -> Path:
    if not project.config.get("auto_folder_name"):
        return project.root
    base = project.config.get("folder_base")
    if not base:
        return project.root
    clean_title = safe_filename(str(title or project.config.get("folder_title") or ""), 80)
    new_name = f"{base}_{clean_title}" if clean_title else base
    new_root = project.root.parent / new_name
    if new_root == project.root:
        project.config["folder_name"] = new_root.name
        project.config["folder_title"] = clean_title
        project.save()
        return project.root
    counter = 2
    candidate = new_root
    while candidate.exists():
        candidate = project.root.parent / f"{new_name} ({counter})"
        counter += 1
    shutil.move(str(project.root), str(candidate))
    project.root = candidate
    project.config["folder_name"] = candidate.name
    project.config["folder_title"] = clean_title
    project.save()
    eprint(f"folder: {candidate.name}")
    return candidate


def validate_project(project: Project) -> dict[str, Any]:
    errors: list[str] = []
    md = project.p("02_transcript.md")
    if not md.exists() or len(md.read_text(encoding="utf-8")) < 500:
        errors.append("02_transcript.md is missing or too short (<500 chars)")
    script = load_json(project.p("03_script.json"))
    if not isinstance(script, dict):
        errors.append("03_script.json is missing or invalid")
        script = {}
    segments = script.get("segments") if isinstance(script.get("segments"), list) else []
    max_segments = int(project.config.get("max_segments") or 60)
    if not 2 <= len(segments) <= max_segments:
        errors.append(f"03_script.json must contain 2-{max_segments} segments (got {len(segments)})")
    total = 0.0
    for index, segment in enumerate(segments, 1):
        narration = str(segment.get("narration") or "").strip()
        if not 60 <= len(narration) <= 260:
            errors.append(f"segment {index}: narration must be 60-260 chars (got {len(narration)})")
        try:
            est = float(segment.get("est_seconds") or 0)
        except (TypeError, ValueError):
            est = 0
        if est:
            total += est
    mode = str(project.config.get("duration_mode") or script.get("duration_mode") or "fixed")
    duration_min = project.config.get("duration_min")
    duration_max = project.config.get("duration_max")
    if mode == "range" and duration_min is not None and duration_max is not None:
        low = float(duration_min) * 60 * 0.85
        high = float(duration_max) * 60 * 1.15
        if segments and not low <= total <= high:
            errors.append(f"estimated duration {total:.0f}s is outside the requested range {duration_min}-{duration_max} min")
    elif mode != "unlimited":
        target = float(script.get("target_seconds") or project.config.get("minutes", 3) * 60)
        if segments and abs(total - target) / max(1, target) > 0.25:
            errors.append(f"estimated duration {total:.0f}s is more than 25% away from target {target:.0f}s")
    metadata = load_json(project.p("04_metadata.json"))
    if not isinstance(metadata, dict):
        errors.append("04_metadata.json is missing or invalid")
        metadata = {}
    title = str(metadata.get("title") or "").strip()
    if not title:
        errors.append("metadata.title is empty")
    elif len(title) > 60:
        errors.append(f"metadata.title is too long ({len(title)} chars)")
    tags = metadata.get("tags")
    if not isinstance(tags, list) or len(tags) != 10:
        errors.append(f"metadata.tags must contain exactly 10 items (got {len(tags) if isinstance(tags, list) else 0})")
    prompts = load_json(project.p("05_image_prompts.json"))
    scenes = prompts.get("scenes") if isinstance(prompts, dict) else None
    if not isinstance(scenes, list) or len(scenes) != len(segments):
        errors.append("05_image_prompts.json scenes must match 03_script.json segments")
    else:
        for index, scene in enumerate(scenes, 1):
            prompt = str(scene.get("prompt") or "")
            if len(prompt.split()) < 25:
                errors.append(f"image prompt {index} is too short (<25 words)")
    if errors:
        raise VcsError("validation failed:\n- " + "\n- ".join(errors))
    attach_source(project, metadata)
    write_json(project.p("04_metadata.json"), metadata)
    project.mark("cleanup", [md])
    project.mark("script", [project.p("03_script.json")], segments=len(segments), est_seconds=total)
    project.mark("metadata", [project.p("04_metadata.json")], tags=len(tags))
    project.mark("prompts", [project.p("05_image_prompts.json")], scenes=len(scenes))
    maybe_rename_project_folder(project, title)
    return {"segments": len(segments), "est_seconds": total, "title": title, "duration_mode": mode}


def cmd_validate(args: argparse.Namespace) -> int:
    project = Project.load(Path(args.project).expanduser()) if args.project else latest_project()
    if project is None:
        raise VcsError("no project found; pass --project")
    result = validate_project(project)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------------------
# M2: HTTP text providers with ordered fallback
# ---------------------------------------------------------------------------

def load_prompt(name: str) -> str:
    path = SKILL_ROOT / "references" / "prompts" / name
    if not path.exists():
        raise VcsError(f"prompt not found: {path}")
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```(?:text)?\s*\n(.*?)```", text, re.S)
    return match.group(1).strip() if match else text.strip()


def render_prompt(template: str, values: dict[str, Any]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
        rendered = rendered.replace("{{ " + key + " }}", str(value))
    return rendered


def duration_plan(project: Project) -> dict[str, Any]:
    cfg = project.config
    cps = float(cfg.get("chars_per_second") or 5.1)
    seg_min, seg_max = [int(v) for v in (cfg.get("segment_seconds") or [20, 40])]
    target_segment = int(cfg.get("target_segment_seconds") or 30)
    mode = str(cfg.get("duration_mode") or "fixed")
    if mode == "range":
        low = float(cfg.get("duration_min") or 1)
        high = float(cfg.get("duration_max") or low)
        min_seconds, max_seconds = low * 60, high * 60
        target_seconds = (low + high) * 30
        instruction = f"总时长 {low:g}–{high:g} 分钟"
    elif mode == "unlimited":
        min_seconds, max_seconds = 60.0, None
        target_seconds = 0
        instruction = "按素材自然展开，不设上限；至少 1 分钟"
    else:
        minutes = float(cfg.get("minutes") or 6)
        min_seconds = max_seconds = minutes * 60
        target_seconds = minutes * 60
        instruction = f"总时长约 {minutes:g} 分钟"
    if max_seconds is None:
        min_chars, max_chars = int(min_seconds * cps), 20000
        min_segments, max_segments = 2, int(cfg.get("max_segments") or 60)
    else:
        min_chars, max_chars = int(min_seconds * cps * 0.9), int(max_seconds * cps * 1.1)
        min_segments = max(2, int(min_seconds // seg_max))
        max_segments = min(int(cfg.get("max_segments") or 60), max(min_segments, int((max_seconds + seg_min - 1) // seg_min)))
    return {
        "mode": mode,
        "duration_instruction": instruction,
        "target_seconds": int(target_seconds),
        "min_chars": min_chars,
        "max_chars": max_chars,
        "min_segments": min_segments,
        "max_segments": max_segments,
        "min_sec": seg_min,
        "max_sec": seg_max,
        "target_sec": target_segment,
        "chars_per_second": cps,
        "language": cfg.get("language", "zh"),
    }


def _try_text_profiles(profiles: list[dict[str, Any]], prompt: str, *, json_mode: bool, transform):
    errors: list[str] = []
    for profile in profiles:
        name = str(profile.get("name") or "unnamed")
        try:
            text = call_text_api(profile, prompt, json_mode=json_mode)
            return transform(text)
        except Exception as exc:  # noqa: BLE001 - try the next API
            errors.append(f"{name}: {exc}")
            eprint(f"text profile {name} failed: {exc}")
    raise VcsError("all text profiles failed: " + " | ".join(errors))


def text_project(project: Project, stage: str, providers_path: str | None = None) -> None:
    providers = load_providers(providers_path, project_root=project.root)
    profiles = text_profiles(providers)
    if not profiles:
        raise VcsError(
            "no HTTP text profiles configured. Add at least one non-agent profile to providers.json "
            "(or keep using Agent mode by writing the files directly)."
        )
    plan = duration_plan(project)
    stages = ["cleanup", "script", "metadata", "prompts"] if stage == "all" else [stage]

    if "cleanup" in stages:
        raw_path = project.p("01_transcript.raw.txt")
        if not raw_path.exists():
            raise VcsError("01_transcript.raw.txt is missing")
        prompt = render_prompt(load_prompt("01_cleanup.md"), {"transcript": raw_path.read_text(encoding="utf-8")})
        text = _try_text_profiles(
            profiles, prompt, json_mode=False,
            transform=lambda value: value if len(value) >= 500 else (_ for _ in ()).throw(VcsError("cleanup result too short")),
        )
        project.p("02_transcript.md").write_text(text.strip() + "\n", encoding="utf-8")
        project.mark("cleanup", [project.p("02_transcript.md")], provider="http")
        eprint("text: cleanup done")

    if "script" in stages:
        md_path = project.p("02_transcript.md")
        if not md_path.exists():
            raise VcsError("02_transcript.md is missing; run cleanup first")
        values = dict(plan)
        values.update({
            "minutes": project.config.get("minutes") or "不限",
            "transcript_md": md_path.read_text(encoding="utf-8"),
            "min_chars": plan["min_chars"], "max_chars": plan["max_chars"],
        })
        prompt = render_prompt(load_prompt("02_script.md"), values)
        script = _try_text_profiles(
            profiles, prompt, json_mode=True,
            transform=lambda value: _validate_script_shape(parse_json_response(value)),
        )
        script.setdefault("duration_mode", plan["mode"])
        write_json(project.p("03_script.json"), script)
        project.mark("script", [project.p("03_script.json")], provider="http")
        eprint("text: script done")

    if "metadata" in stages:
        script_path = project.p("03_script.json")
        if not script_path.exists():
            raise VcsError("03_script.json is missing; run script first")
        prompt = render_prompt(load_prompt("03_metadata.md"), {
            "script_json": json.dumps(load_json(script_path), ensure_ascii=False),
        })
        metadata = _try_text_profiles(
            profiles, prompt, json_mode=True,
            transform=lambda value: _validate_metadata_shape(parse_json_response(value)),
        )
        attach_source(project, metadata)
        write_json(project.p("04_metadata.json"), metadata)
        maybe_rename_project_folder(project, metadata.get("title"))
        project.mark("metadata", [project.p("04_metadata.json")], provider="http")
        eprint("text: metadata done")

    if "prompts" in stages:
        script_path = project.p("03_script.json")
        if not script_path.exists():
            raise VcsError("03_script.json is missing; run script first")
        script = load_json(script_path, {})
        segments = script.get("segments") or []
        template_name = "04_image_16x9.md" if project.config.get("orientation") == "landscape" else "05_image_9x16.md"
        template = load_prompt(template_name)
        scenes = []
        for segment in segments:
            prompt = render_prompt(template, {"narration": segment.get("narration", "")})
            result = _try_text_profiles(
                profiles, prompt, json_mode=True,
                transform=lambda value: _validate_prompt_shape(parse_json_response(value)),
            )
            scenes.append({
                "id": int(segment["id"]),
                "prompt": result["prompt"],
                "seed": 1000 + int(segment["id"]),
            })
        data = {
            "version": 1,
            "orientation": project.config.get("orientation", "portrait"),
            "style": project.config.get("style", "cinematic"),
            "negative": "text, letters, watermark, logo, split screen, collage, multiple panels, deformed hands, extra fingers, oversaturated, plastic skin",
            "scenes": scenes,
        }
        write_json(project.p("05_image_prompts.json"), data)
        project.mark("prompts", [project.p("05_image_prompts.json")], provider="http")
        eprint(f"text: prompts done ({len(scenes)})")


def _validate_script_shape(data: dict[str, Any]) -> dict[str, Any]:
    segments = data.get("segments")
    if not isinstance(segments, list) or not 2 <= len(segments) <= 60:
        raise VcsError("script response must contain 2-60 segments")
    for index, segment in enumerate(segments, 1):
        if not str(segment.get("narration") or "").strip():
            raise VcsError(f"segment {index} has no narration")
        segment.setdefault("id", index)
        segment.setdefault("est_seconds", 30)
    return data


def _validate_metadata_shape(data: dict[str, Any]) -> dict[str, Any]:
    if not str(data.get("title") or "").strip():
        raise VcsError("metadata response has no title")
    tags = data.get("tags")
    if not isinstance(tags, list) or len(tags) != 10:
        raise VcsError("metadata response must contain exactly 10 tags")
    return data


def _validate_prompt_shape(data: dict[str, Any]) -> dict[str, Any]:
    prompt = str(data.get("prompt") or "").strip()
    if len(prompt.split()) < 10:
        raise VcsError("image prompt response is too short")
    return {"id": data.get("id"), "prompt": prompt}


def cmd_text(args: argparse.Namespace) -> int:
    project = Project.load(Path(args.project).expanduser()) if args.project else latest_project()
    if project is None:
        raise VcsError("no project found; pass --project")
    text_project(project, args.stage, providers_path=args.providers or None)
    print(project.root)
    return 0


# ---------------------------------------------------------------------------
# M3: ModelScope images
# ---------------------------------------------------------------------------

def _http_json(url: str, payload: dict[str, Any] | None, headers: dict[str, str], timeout: int = 60) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")[:500]
        raise VcsError(f"HTTP {exc.code} for {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise VcsError(f"network error for {url}: {exc.reason}") from exc


def _download(url: str, path: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            path.write_bytes(resp.read())
    except urllib.error.HTTPError as exc:
        raise VcsError(f"image download failed HTTP {exc.code}") from exc


def _modelscope_image(
    prompt: str, negative: str, output: Path, *,
    api_key: str, base_url: str, model: str, size: str, seed: int,
) -> None:
    if not api_key:
        raise VcsError("missing ModelScope API key for this profile")
    base = (base_url or "https://api-inference.modelscope.cn").rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-ModelScope-Async-Mode": "true",
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "negative_prompt": negative,
        "seed": seed,
    }
    data = _http_json(f"{base}/images/generations", payload, headers, timeout=180)
    if data.get("images"):
        first = data["images"][0]
        _download(first["url"] if isinstance(first, dict) else first, output)
        return
    task_id = data.get("task_id")
    if not task_id:
        raise VcsError(f"ModelScope returned neither images nor task_id: {data}")
    poll_headers = {
        "Authorization": f"Bearer {api_key}",
        "X-ModelScope-Task-Type": "image_generation",
    }
    deadline = time.time() + 600
    while time.time() < deadline:
        time.sleep(15)
        status = _http_json(f"{base}/tasks/{task_id}", None, poll_headers, timeout=30)
        state = status.get("task_status")
        if state == "SUCCEED":
            images = status.get("output_images") or []
            if not images:
                raise VcsError(f"ModelScope task {task_id} succeeded without images")
            _download(images[0], output)
            return
        if state == "FAILED":
            raise VcsError(f"ModelScope task {task_id} failed: {status}")
    raise VcsError(f"ModelScope task {task_id} timed out after 600s")


def images_project(
    project: Project, *, provider: str | None = None, limit: int | None = None,
    providers_path: str | None = None,
) -> None:
    prompts = load_json(project.p("05_image_prompts.json"))
    if not isinstance(prompts, dict) or not isinstance(prompts.get("scenes"), list):
        raise VcsError("05_image_prompts.json is missing or invalid; run `vcs validate` first")
    provider = provider or project.config.get("providers", {}).get("image", "modelscope")
    orientation = project.config.get("orientation", "portrait")
    legacy_sizes = {"928x1664", "1664x928"}
    size = project.config.get("image_size")
    if not size or size in legacy_sizes:
        size = image_size_for(
            int(project.config.get("width") or (1080 if orientation == "portrait" else 1920)),
            int(project.config.get("height") or (1920 if orientation == "portrait" else 1080)),
        )
    negative = prompts.get("negative", "")
    image_dir = project.p("06_images")
    image_dir.mkdir(parents=True, exist_ok=True)
    scenes = prompts["scenes"][:limit] if limit else prompts["scenes"]

    providers = load_providers(providers_path, project_root=project.root)
    if provider == "mock":
        profiles: list[dict[str, Any]] = [{"name": "mock", "provider": "mock"}]
    else:
        profiles = [p for p in image_profiles(providers) if p.get("provider") == "modelscope"]
    if not profiles:
        raise VcsError("no image profiles configured; add image profiles to providers.json or use --provider mock")

    disabled: set[str] = set()
    lock = threading.Lock()
    failures: list[str] = []

    def generate(scene: dict[str, Any]) -> Path:
        scene_id = int(scene["id"])
        path = image_dir / f"scene_{scene_id:03d}.jpg"
        want = tuple(int(v) for v in size.split("x"))
        if path.exists() and path.stat().st_size > 1024:
            try:
                if ffprobe_size(path) == want:
                    return path
            except VcsError:
                pass
        if provider == "mock":
            width, height = (int(project.config.get("width") or 1080), int(project.config.get("height") or 1920))
            mock_image(path, width, height, scene_id)
        else:
            last_error: Exception | None = None
            for profile in profiles:
                name = str(profile.get("name") or "unnamed")
                with lock:
                    if name in disabled:
                        continue
                key = resolve_api_key(profile)
                base = str(profile.get("base_url") or os.environ.get("VCS_MODELSCOPE_BASE_URL") or "https://api-inference.modelscope.cn")
                model = str(profile.get("model") or project.config.get("models", {}).get("image") or DEFAULTS["image_model"])
                try:
                    tmp = image_dir / f".scene_{scene_id:03d}.download"
                    _modelscope_image(
                        str(scene["prompt"]), str(negative), tmp,
                        api_key=key, base_url=base, model=model, size=size,
                        seed=int(scene.get("seed") or 1000 + scene_id),
                    )
                    want = tuple(int(v) for v in size.split("x"))
                    run([
                        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(tmp),
                        "-vf", f"scale={want[0]}:{want[1]}:force_original_aspect_ratio=increase:flags=lanczos,"
                               f"crop={want[0]}:{want[1]},setsar=1",
                        "-frames:v", "1", "-q:v", "2", str(path),
                    ])
                    tmp.unlink(missing_ok=True)
                    last_error = None
                    break
                except Exception as exc:  # noqa: BLE001 - try the next account/key
                    last_error = exc
                    with lock:
                        disabled.add(name)
                        failures.append(f"{name}: {exc}")
                    eprint(f"image profile {name} failed: {exc}")
            if last_error is not None:
                raise VcsError(f"all image profiles failed for scene {scene_id}: {last_error}")
        width, height = ffprobe_size(path)
        want = tuple(int(v) for v in size.split("x"))
        if (width, height) != want:
            raise VcsError(f"image size mismatch: {path} is {width}x{height}, expected {size}")
        return path

    paths: list[Path] = []
    with ThreadPoolExecutor(max_workers=min(3, len(scenes) or 1)) as pool:
        futures = [pool.submit(generate, scene) for scene in scenes]
        for future in futures:
            paths.append(future.result())
    project.mark("images", sorted(paths), provider=provider, profiles=[p.get("name") for p in profiles])
    eprint(f"images: {len(paths)}")

def cmd_images(args: argparse.Namespace) -> int:
    project = Project.load(Path(args.project).expanduser()) if args.project else latest_project()
    if project is None:
        raise VcsError("no project found; pass --project")
    images_project(project, provider=args.provider or None, limit=args.limit or None, providers_path=args.providers or None)
    print(project.root)
    return 0


# ---------------------------------------------------------------------------
# M3: local Qwen3-TTS
# ---------------------------------------------------------------------------

TTS_REFERENCE = {
    "female": ("voice_female.mp3", "你好，早上好，再见。今天天气真好，我们一起出去玩吧。你想要吃什么？"),
    "male": ("voice_male.mp3", "你好，早上好，再见。今天天气真好，我们一起出去玩吧。你想要吃什么？"),
}


def tts_project(
    project: Project, *, limit: int | None = None,
    voice_ref: str | None = None, voice_ref_text: str | None = None,
) -> None:
    script = load_json(project.p("03_script.json"))
    if not isinstance(script, dict) or not isinstance(script.get("segments"), list):
        raise VcsError("03_script.json is missing or invalid; run `vcs validate` first")
    model_id = project.config.get("models", {}).get("tts", "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16")
    voice = str(project.config.get("voice") or "female").lower()
    audio_dir = project.p("audio")
    audio_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(default_hf_home()))
    import mlx.core as mx
    from mlx_audio.tts.generate import generate_audio
    from mlx_audio.tts.utils import load_model

    eprint(f"tts: loading {model_id}")
    model = load_model(model_id)
    ref_name, default_ref_text = TTS_REFERENCE.get(voice, TTS_REFERENCE["female"])
    ref_text = str(voice_ref_text or default_ref_text)
    if voice_ref:
        ref_path = Path(voice_ref).expanduser()
        if not ref_path.exists():
            raise VcsError(f"voice reference not found: {ref_path}")
    else:
        candidate = SKILL_ROOT / "assets" / ref_name
        ref_path = candidate if candidate.exists() else None
    if ref_path is None:
        raise VcsError(
            "reference audio is required. Add voice_female.mp3/voice_male.mp3 to assets/, "
            "or pass --voice-ref <audio> and --voice-ref-text <transcript>."
        )
    segments = script["segments"][:limit] if limit else script["segments"]
    paths: list[Path] = []
    for index, segment in enumerate(segments, 1):
        scene_id = int(segment["id"])
        out = audio_dir / f"scene_{scene_id:03d}.wav"
        if out.exists() and out.stat().st_size > 1024:
            paths.append(out)
            continue
        eprint(f"tts: {index}/{len(segments)} scene {scene_id}")
        mx.random.seed(42)
        prefix = out.with_suffix("")
        generate_audio(
            model=model,
            text=str(segment["narration"]) + "。。",
            voice=voice,
            lang_code="chinese",
            temperature=0.35,
            top_p=0.85,
            ref_audio=str(ref_path) if ref_path else None,
            ref_text=ref_text if ref_path else None,
            join_audio=True,
            file_prefix=str(prefix),
        )
        generated = [p for p in audio_dir.glob(f"scene_{scene_id:03d}*.wav") if p.exists()]
        if not generated:
            raise VcsError(f"TTS did not generate audio for scene {scene_id}")
        chosen = max(generated, key=lambda p: p.stat().st_mtime)
        if chosen != out:
            chosen.replace(out)
        tmp = out.with_suffix(".tail.wav")
        run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(out), "-f", "lavfi", "-t", "0.35", "-i", "anullsrc=r=24000:cl=mono",
            "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1", "-c:a", "pcm_s16le", str(tmp),
        ])
        tmp.replace(out)
        # keep every scene inside the requested 20-40s window
        if ffprobe_duration(out) < 20.0:
            padded = out.with_suffix(".pad.wav")
            run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(out),
                "-af", "apad=whole_dur=20.0", "-c:a", "pcm_s16le", str(padded),
            ])
            padded.replace(out)
        paths.append(out)
    project.mark("tts", sorted(paths), model=model_id, voice=voice)
    eprint(f"tts: {len(paths)}")


def cmd_tts(args: argparse.Namespace) -> int:
    project = Project.load(Path(args.project).expanduser()) if args.project else latest_project()
    if project is None:
        raise VcsError("no project found; pass --project")
    tts_project(
        project, limit=args.limit or None,
        voice_ref=args.voice_ref or None, voice_ref_text=args.voice_ref_text or None,
    )
    print(project.root)
    return 0


# ---------------------------------------------------------------------------
# M3: compose + finalize from real assets
# ---------------------------------------------------------------------------

def compose_project(project: Project, *, keep_intermediates: bool = False) -> Path:
    script = load_json(project.p("03_script.json"))
    metadata = load_json(project.p("04_metadata.json"))
    if not isinstance(script, dict) or not isinstance(metadata, dict):
        raise VcsError("03_script.json or 04_metadata.json is missing")
    attach_source(project, metadata)
    write_json(project.p("04_metadata.json"), metadata)
    maybe_rename_project_folder(project, metadata.get("title"))
    clips: list[Path] = []
    for segment in script["segments"]:
        scene_id = int(segment["id"])
        image = scene_image_path(project, scene_id)
        audio = project.p("audio", f"scene_{scene_id:03d}.wav")
        for need in (image, audio):
            if not need.exists():
                raise VcsError(f"missing compose input: {need}")
        clip = project.p("clips", f"scene_{scene_id:03d}.mp4")
        if not clip.exists() or clip.stat().st_size < 1024:
            compose_clip(image, audio, clip, project.config)
        clips.append(clip)
    merged = project.p(".merged.mp4")
    concat_clips(clips, merged)
    project.mark("compose", [merged], clips=len(clips))
    title = safe_filename(str(metadata.get("title") or "video"))
    final_path = project.p(f"07_{title}.mp4")
    counter = 2
    while final_path.exists():
        final_path = project.p(f"07_{title} ({counter}).mp4")
        counter += 1
    shutil.move(str(merged), str(final_path))
    project.mark("finalize", [final_path], title=title)
    if not keep_intermediates:
        cleanup_intermediates(project)
    return final_path


def cleanup_intermediates(project: Project) -> None:
    """Keep only publish/review artifacts: transcripts, metadata, prompts, script, images, final mp4."""
    for folder in ("audio", "clips", "logs"):
        path = project.p(folder)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    for path in (project.p(".merged.mp4"), project.p("clips.txt")):
        path.unlink(missing_ok=True)
    final_dir = project.p("final")
    if final_dir.exists():
        shutil.rmtree(final_dir, ignore_errors=True)
    source_dir = project.p("source")
    if source_dir.exists():
        if project.config.get("input_type") == "pdf":
            for path in source_dir.iterdir():
                if path.is_file() and path.suffix.lower() != ".pdf":
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
        else:
            shutil.rmtree(source_dir, ignore_errors=True)
    for path in project.root.rglob(".DS_Store"):
        path.unlink(missing_ok=True)
    state = project.state()
    for stage in ("tts", "compose"):
        if stage in state.get("stages", {}):
            state["stages"][stage]["status"] = "cleaned"
            state["stages"][stage]["outputs"] = []
    write_json(project.state_path, state)
    eprint("cleanup: removed audio/, clips/, logs/, temp files; kept 01–07 artifacts")


def cmd_rename(args: argparse.Namespace) -> int:
    project = Project.load(Path(args.project).expanduser()) if args.project else latest_project()
    if project is None:
        raise VcsError("no project found; pass --project")
    if not project.config.get("folder_base"):
        created = str(project.config.get("created_at") or "")
        try:
            date_part = datetime.fromisoformat(created).strftime("%m%d%Y")
        except ValueError:
            date_part = datetime.now().strftime("%m%d%Y")
        label = str(project.config.get("source_label") or _source_label(project.config.get("input") or None, str(project.config.get("input_type") or "text"), bool(project.config.get("mock"))))
        project.config["folder_base"] = f"{label}_{date_part}"
    project.config["auto_folder_name"] = True
    metadata = load_json(project.p("04_metadata.json"), {})
    title = str((metadata or {}).get("title") or project.config.get("folder_title") or "")
    maybe_rename_project_folder(project, title)
    print(project.root)
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    project = Project.load(Path(args.project).expanduser()) if args.project else latest_project()
    if project is None:
        raise VcsError("no project found; pass --project")
    cleanup_intermediates(project)
    print(project.root)
    return 0


def cmd_compose(args: argparse.Namespace) -> int:
    project = Project.load(Path(args.project).expanduser()) if args.project else latest_project()
    if project is None:
        raise VcsError("no project found; pass --project")
    print(compose_project(project, keep_intermediates=args.keep_intermediates))
    return 0


# ---------------------------------------------------------------------------
# compose
# ---------------------------------------------------------------------------

def compose_clip(image: Path, audio: Path, output: Path, config: dict[str, Any]) -> None:
    width, height, fps = int(config["width"]), int(config["height"]), int(config["fps"])
    ff = config["ffmpeg"]
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={width}:{height},setsar=1,format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-framerate", str(fps), "-i", str(image),
        "-i", str(audio),
        "-vf", vf,
        "-c:v", "libx264", "-preset", str(ff["preset"]), "-crf", str(ff["crf"]),
        "-profile:v", "high", "-level", "4.1",
        "-g", str(ff["gop"]), "-keyint_min", str(fps), "-sc_threshold", "0",
        "-c:a", "aac", "-b:a", str(ff["audio_bitrate"]), "-ar", "48000", "-ac", "2",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-shortest", "-movflags", "+faststart", str(output),
    ])
    if not output.exists():
        raise VcsError(f"compose produced no output: {output}")


def concat_clips(clips: list[Path], output: Path) -> None:
    list_path = output.parent / "clips.txt"
    list_path.write_text(
        "\n".join(f"file '{clip.resolve()}'" for clip in clips) + "\n",
        encoding="utf-8",
    )
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-c", "copy", "-movflags", "+faststart", str(output),
    ])


# ---------------------------------------------------------------------------
# pipeline
# ---------------------------------------------------------------------------

def run_pipeline(project: Project, *, mock: bool) -> Path:
    config = project.config
    if not mock:
        raise VcsError(
            "real providers are not wired yet (M1-M3). "
            "Run with --mock to exercise the full pipeline, or use `vcs text`/`vcs images` "
            "after configuring ModelScope/MLX providers."
        )

    log_path = project.p("logs", "run.log")
    log_path.write_text(f"[{now_iso()}] start mock pipeline\n", encoding="utf-8")

    # 1. script
    script = mock_script(config)
    write_json(project.p("03_script.json"), script)
    project.mark("script", [project.p("03_script.json")], provider="mock", model="mock")
    eprint(f"[1/6] script: {len(script['segments'])} segments")

    # 2. metadata
    metadata = mock_metadata(script)
    attach_source(project, metadata)
    write_json(project.p("04_metadata.json"), metadata)
    maybe_rename_project_folder(project, metadata.get("title"))
    project.mark("metadata", [project.p("04_metadata.json")], provider="mock")
    eprint(f"[2/6] metadata: {metadata['title']}")

    # 3. image prompts
    prompts = mock_image_prompts(script, config)
    write_json(project.p("05_image_prompts.json"), prompts)
    project.mark("prompts", [project.p("05_image_prompts.json")], orientation=config["orientation"])
    eprint(f"[3/6] prompts: {len(prompts['scenes'])}")

    # 4. images
    image_dir = project.p("06_images")
    for scene in prompts["scenes"]:
        scene_id = int(scene["id"])
        path = image_dir / f"scene_{scene_id:03d}.jpg"
        if not path.exists():
            mock_image(path, int(config["width"]), int(config["height"]), scene_id)
    project.mark("images", sorted(image_dir.glob("scene_*.jpg")), provider="mock")
    eprint(f"[4/6] images: {len(list(image_dir.glob('scene_*.jpg')))}")

    # 5. tts
    audio_dir = project.p("audio")
    for segment in script["segments"]:
        scene_id = int(segment["id"])
        path = audio_dir / f"scene_{scene_id:03d}.wav"
        if not path.exists():
            duration = max(2.0, min(60.0, float(segment["est_seconds"]) + 0.35))
            mock_audio(path, duration)
    project.mark("tts", sorted(audio_dir.glob("scene_*.wav")), provider="mock")
    eprint(f"[5/6] tts: {len(list(audio_dir.glob('scene_*.wav')))}")

    # 6. compose
    clips = []
    for segment in script["segments"]:
        scene_id = int(segment["id"])
        image = scene_image_path(project, scene_id)
        audio = audio_dir / f"scene_{scene_id:03d}.wav"
        clip = project.p("clips", f"scene_{scene_id:03d}.mp4")
        if not clip.exists():
            compose_clip(image, audio, clip, config)
        clips.append(clip)
    merged = project.p(".merged.mp4")
    concat_clips(clips, merged)
    project.mark("compose", [merged], clips=len(clips))
    eprint(f"[6/6] compose: {ffprobe_duration(merged):.1f}s")

    # 7. finalize
    title = safe_filename(metadata["title"])
    final_path = project.p(f"07_{title}.mp4")
    counter = 2
    while final_path.exists():
        final_path = project.p(f"07_{title} ({counter}).mp4")
        counter += 1
    shutil.move(str(merged), str(final_path))
    project.mark("finalize", [final_path], title=metadata["title"])
    eprint(f"done: {final_path} ({human_size(final_path.stat().st_size)})")
    cleanup_intermediates(project)
    return final_path


def create_project(args: argparse.Namespace, *, mock: bool) -> Project:
    input_path = args.input
    if input_path and not Path(input_path).expanduser().exists() and not input_path.startswith(("http://", "https://")):
        raise VcsError(f"input not found: {input_path}")

    config = build_config(args, input_path=input_path, mock=mock)
    if args.out:
        root = Path(args.out).expanduser()
    else:
        base = config["folder_base"]
        root = DEFAULT_PROJECT_PARENT / base
        counter = 2
        while root.exists() and any(root.iterdir()):
            root = DEFAULT_PROJECT_PARENT / f"{base}_{counter}"
            counter += 1
        config["folder_base"] = config["folder_name"] = root.name

    if root.exists() and any(root.iterdir()):
        if not args.force:
            raise VcsError(f"project directory is not empty: {root} (use --force to reuse)")
    project = Project.create(root, config)
    if input_path and Path(input_path).expanduser().exists():
        source = project.p("source", Path(input_path).name)
        if not source.exists():
            shutil.copy2(Path(input_path).expanduser(), source)
    return project


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def _interactive_config(args: argparse.Namespace) -> None:
    if not sys.stdin.isatty():
        raise VcsError("--interactive requires a terminal; pass flags instead (see --help)")
    print("生成前配置（直接回车用默认值）")
    orientation = input("画幅 [1=竖屏 9:16, 2=横屏 16:9] (默认 1): ").strip()
    if orientation in {"2", "landscape", "横屏"}:
        args.orientation = "landscape"
    elif orientation in {"1", "portrait", "竖屏"}:
        args.orientation = "portrait"
    duration = input("时长 [如 6 / 5-8 / unlimited] (默认 6): ").strip()
    if duration:
        args.duration = duration
        args.minutes = None
    segment = input("每段秒数范围 [默认 20-40]: ").strip()
    if segment:
        args.segment_range = segment
    voice = input("音色 [female/male] (默认 female): ").strip()
    if voice:
        args.voice = voice
    style = input("风格 [cinematic/documentary/anime] (默认 cinematic): ").strip()
    if style:
        args.style = style


def cmd_config(args: argparse.Namespace) -> int:
    project = Project.load(Path(args.project).expanduser()) if args.project else latest_project()
    if project is None:
        raise VcsError("no project found; pass --project")
    cfg = project.config
    old = dict(cfg)
    changed: set[str] = set()
    invalid: set[str] = set()

    if args.orientation:
        cfg["orientation"] = args.orientation
        changed.add("orientation")
    if args.width or args.height:
        width = int(args.width or cfg.get("width", 1080))
        height = int(args.height or cfg.get("height", 1920))
        cfg["width"], cfg["height"] = width, height
        changed.add("resolution")
    elif args.orientation:
        cfg["width"], cfg["height"] = (1080, 1920) if args.orientation == "portrait" else (1920, 1080)
    if args.fps:
        cfg["fps"] = int(args.fps)
        cfg.setdefault("ffmpeg", {})["gop"] = int(args.fps) * 2
        changed.add("fps")
    cfg["image_size"] = image_size_for(int(cfg["width"]), int(cfg["height"]))

    if args.duration or args.unlimited or args.minutes is not None:
        probe = argparse.Namespace(
            duration=args.duration, unlimited=args.unlimited, minutes=args.minutes,
            segment_range=f"{cfg.get('segment_seconds', [20, 40])[0]}-{cfg.get('segment_seconds', [20, 40])[1]}",
            segment=cfg.get("target_segment_seconds", 30),
        )
        mode, low, high = _parse_duration(probe)
        cfg.update({"duration_mode": mode, "duration_min": low, "duration_max": high})
        cfg["minutes"] = round((low + high) / 2, 2) if mode == "range" else (low or 0.0)
        changed.add("duration")

    if args.segment_range or args.segment:
        cur = cfg.get("segment_seconds") or [20, 40]
        probe = argparse.Namespace(
            segment_range=args.segment_range or f"{cur[0]}-{cur[1]}",
            segment=args.segment or cfg.get("target_segment_seconds", 30),
        )
        low, high, target = _parse_segment_range(probe)
        cfg["segment_seconds"] = [low, high]
        cfg["target_segment_seconds"] = target
        changed.add("segment")

    if args.voice:
        cfg["voice"] = args.voice
        changed.add("voice")
    if args.style:
        cfg["style"] = args.style
        changed.add("style")

    if "orientation" in changed or "resolution" in changed:
        invalid |= {"prompts", "images", "compose", "finalize"}
    if "duration" in changed or "segment" in changed:
        invalid |= {"script", "metadata", "prompts", "images", "tts", "compose", "finalize"}
    if "voice" in changed:
        invalid |= {"tts", "compose", "finalize"}
    if "style" in changed:
        invalid |= {"prompts", "images", "compose", "finalize"}

    if invalid:
        state = project.state()
        for stage in invalid:
            state.get("stages", {}).pop(stage, None)
        write_json(project.state_path, state)
        if "script" in invalid:
            for name in ("03_script.json", "04_metadata.json"):
                project.p(name).unlink(missing_ok=True)
        if "prompts" in invalid:
            project.p("05_image_prompts.json").unlink(missing_ok=True)
        if "images" in invalid:
            for path in project.p("06_images").glob("*"):
                if path.is_file():
                    path.unlink()
        if "tts" in invalid:
            for path in project.p("audio").glob("*"):
                if path.is_file():
                    path.unlink()
        for path in project.p("clips").glob("*.mp4"):
            path.unlink()
        for path in project.root.glob("07_*.mp4"):
            path.unlink()

    project.save()
    print(json.dumps({
        "project": str(project.root),
        "changed": sorted(changed),
        "invalidated": sorted(invalid),
        "next": "re-run `vcs validate` and then `vcs images` / `vcs tts` / `vcs compose`",
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    print(f"vcs {VERSION}")
    print(f"python {sys.version.split()[0]} ({sys.executable})")
    required = ["ffmpeg", "ffprobe"]
    optional = ["yt-dlp"]
    missing = []
    for tool in required + optional:
        path = shutil.which(tool)
        if not path:
            if tool in required:
                missing.append(tool)
            print(f"  {tool:<8} MISSING (optional)" if tool in optional else f"  {tool:<8} MISSING")
            continue
        if tool == "ffmpeg":
            version = subprocess.run([tool, "-version"], capture_output=True, text=True).stdout.splitlines()[0]
            print(f"  {tool:<8} {version}")
        elif tool == "ffprobe":
            print(f"  {tool:<8} {path}")
        else:
            version = subprocess.run([tool, "--version"], capture_output=True, text=True).stdout.strip()
            print(f"  {tool:<8} {version} (optional)")
    candidates = []
    if os.environ.get("HF_HOME"):
        candidates.append(Path(os.environ["HF_HOME"]) / "hub")
    candidates += [
        default_hf_home() / "hub",
        SKILL_ROOT.parent / ".hf-cache" / "hub",
        Path.home() / ".cache" / "huggingface" / "hub",
    ]
    cache = next((path for path in candidates if path.exists()), candidates[-1])
    if cache.exists():
        size = sum(path.stat().st_size for path in cache.rglob("*") if path.is_file())
        print(f"  HF cache {cache} ({human_size(size)})")
        if size < 1024 * 1024:
            print("           cache is nearly empty; download Qwen3-ASR/TTS models before real runs")
    else:
        print(f"  HF cache {cache} (missing)")
    if missing:
        print(f"error: missing required tools: {', '.join(missing)}")
        return 1
    print("ok")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    if getattr(args, "interactive", False):
        _interactive_config(args)
    project = create_project(args, mock=False)
    print(project.root)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if getattr(args, "interactive", False):
        _interactive_config(args)
    if not args.mock:
        eprint("note: only --mock is implemented in M0; real providers land in M1-M3")
    project = create_project(args, mock=bool(args.mock))
    final = run_pipeline(project, mock=bool(args.mock))
    print(final)
    return 0


def cmd_providers(args: argparse.Namespace) -> int:
    providers = load_providers(args.file)
    for kind in ("text", "image"):
        rows = providers.get(kind) or []
        print(f"[{kind}]")
        for index, profile in enumerate(rows, 1):
            key = resolve_api_key(profile)
            print(
                f"  {index}. {profile.get('name') or 'unnamed':<20} "
                f"provider={profile.get('provider') or '-':<10} "
                f"model={profile.get('model') or '-':<28} "
                f"base={profile.get('base_url') or '-':<40} "
                f"key={'set' if key else 'missing'}"
            )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    selected = getattr(args, "project_opt", None) or args.project
    root = Path(selected).expanduser() if selected else latest_project()
    if root is None:
        raise VcsError("no project found; pass a project path")
    project = Project.load(root)
    print(f"project: {project.root}")
    print(f"input:   {project.config.get('input') or '-'}")
    print(f"format:  {project.config['width']}x{project.config['height']} @ {project.config['fps']}fps")
    stages = project.state().get("stages", {})
    for stage in ("ingest", "asr", "cleanup", "script", "metadata", "prompts", "images", "tts", "compose", "finalize"):
        row = stages.get(stage, {})
        status = row.get("status", "pending")
        detail = ""
        if stage == "images":
            detail = f" ({sum(1 for p in project.p('06_images').glob('scene_*') if p.suffix.lower() in {'.jpg', '.jpeg', '.png'})})"
        elif stage == "tts":
            detail = f" ({len(list(project.p('audio').glob('scene_*.wav')))})"
        print(f"  {stage:<9} {status}{detail}")
    finals = sorted(project.root.glob("07_*.mp4"))
    if finals:
        print(f"final:   {finals[0]} ({human_size(finals[0].stat().st_size)})")
    return 0


def latest_project() -> Path | None:
    candidates: list[Path] = []
    for parent in (DEFAULT_PROJECT_PARENT, Path.cwd() / "runs"):
        if parent.exists():
            candidates.extend(p for p in parent.iterdir() if (p / "project.json").exists())
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


# ---------------------------------------------------------------------------
# cli
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vcs", description="video creation skill CLI")
    parser.add_argument("--version", action="version", version=f"vcs {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_project_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--input", "-i", help="video/article/PDF/text path or URL")
        p.add_argument("--out", help="project directory (default: ./projects/<timestamp>_<name>)")
        p.add_argument("--name", help="project slug")
        p.add_argument("--minutes", type=float, default=None, help="fixed target duration in minutes (kept for compatibility)")
        p.add_argument("--duration", help="fixed minutes, min-max range, or 'unlimited' (e.g. 6 / 5-8 / unlimited)")
        p.add_argument("--unlimited", action="store_true", help="do not cap the video duration")
        p.add_argument("--segment", type=int, default=DEFAULTS["target_segment_seconds"], help="target seconds per segment")
        p.add_argument("--segment-range", help="allowed segment seconds, e.g. 20-40")
        p.add_argument("--orientation", choices=["portrait", "landscape"], default=DEFAULTS["orientation"])
        p.add_argument("--width", type=int, default=0, help="custom output width (overrides orientation preset)")
        p.add_argument("--height", type=int, default=0, help="custom output height (overrides orientation preset)")
        p.add_argument("--interactive", action="store_true", help="ask for orientation/duration/segment/voice before creating")
        p.add_argument("--voice", default=DEFAULTS["voice"])
        p.add_argument("--style", default=DEFAULTS["style"])
        p.add_argument("--language", default=DEFAULTS["language"])
        p.add_argument("--fps", type=int, default=DEFAULTS["fps"])
        p.add_argument("--chars-per-second", type=float, default=DEFAULTS["chars_per_second"])
        p.add_argument("--force", action="store_true", help="reuse a non-empty project directory")

    p_doctor = sub.add_parser("doctor", help="check ffmpeg and local model environment")
    p_doctor.set_defaults(func=cmd_doctor)

    p_init = sub.add_parser("init", help="create a project directory and config")
    add_project_args(p_init)
    p_init.set_defaults(func=cmd_init)

    p_run = sub.add_parser("run", help="run the pipeline")
    add_project_args(p_run)
    p_run.add_argument("--mock", action="store_true", help="run with mock text/image/tts providers")
    p_run.set_defaults(func=cmd_run)

    p_ingest = sub.add_parser("ingest", help="ingest video/audio/article/PDF/text")
    add_project_args(p_ingest)
    p_ingest.add_argument("--project", help="existing project directory")
    p_ingest.add_argument("--type", choices=["auto", "video", "article", "pdf", "text"], default="auto")
    p_ingest.add_argument("--html", help="saved HTML file for an article URL (use when the site blocks bots)")
    p_ingest.set_defaults(func=cmd_ingest)

    p_asr = sub.add_parser("asr", help="transcribe source audio with Qwen3-ASR")
    p_asr.add_argument("--project", help="project directory (default: latest)")
    p_asr.add_argument("--language", default="English")
    p_asr.add_argument("--model", default="")
    p_asr.set_defaults(func=cmd_asr)

    p_text = sub.add_parser("text", help="run text stages through HTTP providers (with fallback)")
    p_text.add_argument("--project", help="project directory (default: latest)")
    p_text.add_argument("--stage", choices=["cleanup", "script", "metadata", "prompts", "all"], default="all")
    p_text.add_argument("--providers", help="providers.json path")
    p_text.set_defaults(func=cmd_text)

    p_validate = sub.add_parser("validate", help="validate agent-written text files")
    p_validate.add_argument("--project", help="project directory (default: latest)")
    p_validate.set_defaults(func=cmd_validate)

    p_images = sub.add_parser("images", help="generate scene images with ModelScope")
    p_images.add_argument("--project", help="project directory (default: latest)")
    p_images.add_argument("--provider", choices=["modelscope", "mock"], default="")
    p_images.add_argument("--limit", type=int, default=0)
    p_images.add_argument("--providers", help="providers.json path (ordered image accounts)")
    p_images.set_defaults(func=cmd_images)

    p_tts = sub.add_parser("tts", help="generate scene audio with local Qwen3-TTS")
    p_tts.add_argument("--project", help="project directory (default: latest)")
    p_tts.add_argument("--limit", type=int, default=0)
    p_tts.add_argument("--voice-ref", help="optional reference audio (wav/mp3) for voice cloning")
    p_tts.add_argument("--voice-ref-text", help="transcript of the reference audio")
    p_tts.set_defaults(func=cmd_tts)

    p_compose = sub.add_parser("compose", help="compose scene clips and final video")
    p_compose.add_argument("--project", help="project directory (default: latest)")
    p_compose.add_argument("--keep-intermediates", action="store_true", help="keep audio/, clips/, logs/")
    p_compose.set_defaults(func=cmd_compose)

    p_rename = sub.add_parser("rename", help="rename an existing project folder to source_date_title")
    p_rename.add_argument("--project", help="project directory (default: latest)")
    p_rename.set_defaults(func=cmd_rename)

    p_clean = sub.add_parser("clean", help="remove audio/, clips/, logs/ and temp files")
    p_clean.add_argument("--project", help="project directory (default: latest)")
    p_clean.set_defaults(func=cmd_clean)

    p_config = sub.add_parser("config", help="change orientation/duration/segment/voice of an existing project")
    p_config.add_argument("--project", help="project directory (default: latest)")
    p_config.add_argument("--orientation", choices=["portrait", "landscape"])
    p_config.add_argument("--duration", help="fixed minutes, min-max range, or 'unlimited'")
    p_config.add_argument("--unlimited", action="store_true")
    p_config.add_argument("--minutes", type=float, default=None)
    p_config.add_argument("--segment-range")
    p_config.add_argument("--segment", type=int, default=None)
    p_config.add_argument("--width", type=int, default=0)
    p_config.add_argument("--height", type=int, default=0)
    p_config.add_argument("--fps", type=int, default=0)
    p_config.add_argument("--voice")
    p_config.add_argument("--style")
    p_config.set_defaults(func=cmd_config)

    p_providers = sub.add_parser("providers", help="list text/image profiles and whether keys are present")
    p_providers.add_argument("--file", help="providers.json path")
    p_providers.set_defaults(func=cmd_providers)

    p_status = sub.add_parser("status", help="show stage status")
    p_status.add_argument("project", nargs="?")
    p_status.add_argument("--project", dest="project_opt", help="project directory")
    p_status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    load_env_files()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except VcsError as exc:
        eprint(f"error: {exc}")
        return 1
    except KeyboardInterrupt:
        eprint("cancelled")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
