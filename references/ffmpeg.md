# ffmpeg 合成参数

## 单段：图片 + 音频

竖屏把 `1080:1920` 换成横屏 `1920:1080`。

```bash
ffmpeg -y -loop 1 -framerate 30 -i images/scene_001.jpg \
  -i audio/scene_001.wav \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,setsar=1,format=yuv420p" \
  -c:v libx264 -preset veryfast -crf 20 -profile:v high -level 4.1 \
  -g 60 -keyint_min 30 -sc_threshold 0 \
  -c:a aac -b:a 128k -ar 48000 -ac 2 \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
  -shortest -movflags +faststart clips/scene_001.mp4
```

## 合并

```bash
printf "file '%s'\n" "$PWD"/clips/*.mp4 > clips.txt
ffmpeg -y -f concat -safe 0 -i clips.txt -c copy -movflags +faststart final/.merged.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 final/.merged.mp4
```

## 要点

- 所有 clip 必须同 codec/profile/level/pix_fmt/分辨率/fps/采样率/声道/GOP，否则 `-c copy` 会静默花屏。
- `setsar=1` 必加；`force_original_aspect_ratio=increase` + `crop` 会留下非方像素。
- `-pix_fmt yuv420p`、`-profile:v high -level 4.1`、`-movflags +faststart` 保证兼容与网页秒开。
- 1080p 下 `h264_videotoolbox` 比 `libx264 veryfast` 慢（本机 187 vs 415 fps），不要默认开。
- 段间留白靠 TTS 尾部静音（350ms），不要用 `-t` 硬拉长视频。

## 可选 Ken Burns

不要用 `-loop 1` + `zoompan d=1`（画面几乎不动）。正确做法：单张静图输入 + `d=帧数`，`fps` 写在 zoompan 内。

```bash
ffmpeg -y -i prep.png -i audio/scene_001.wav \
  -vf "zoompan=z='min(1+0.0006*on,1.15)':d=450:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30,setsar=1,format=yuv420p" \
  -c:v libx264 -preset veryfast -crf 20 -g 60 -keyint_min 30 -sc_threshold 0 \
  -c:a aac -b:a 128k -ar 48000 -ac 2 -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
  -shortest clips/scene_001.mp4
```
