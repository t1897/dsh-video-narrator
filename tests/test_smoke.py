from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
VCS = SKILL / "scripts" / "vcs.py"


class SmokeTest(unittest.TestCase):
    def run_vcs(self, *args: str, timeout: int = 180) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VCS), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(SKILL),
        )

    def test_doctor(self) -> None:
        proc = self.run_vcs("doctor")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ffmpeg", proc.stdout)

    def test_mock_portrait_pipeline(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vcs-test-") as tmp:
            out = Path(tmp) / "project"
            proc = self.run_vcs(
                "run", "--mock", "--minutes", "0.2",
                "--orientation", "portrait", "--out", str(out),
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            finals = list(out.glob("07_*.mp4"))
            self.assertEqual(len(finals), 1, proc.stdout)
            video = finals[0]
            self.assertGreater(video.stat().st_size, 100_000)

            probe = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-show_entries",
                    "stream=codec_type,width,height", "-show_entries",
                    "format=duration", "-of", "json", str(video),
                ],
                capture_output=True, text=True, check=True,
            )
            data = json.loads(probe.stdout)
            streams = {stream["codec_type"]: stream for stream in data["streams"]}
            self.assertEqual(streams["video"]["width"], 1080)
            self.assertEqual(streams["video"]["height"], 1920)
            self.assertIn("audio", streams)
            self.assertGreater(float(data["format"]["duration"]), 5)

            state = json.loads((out / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["finalize"]["status"], "done")

    def test_duration_and_orientation_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vcs-config-") as tmp:
            out = Path(tmp) / "project"
            proc = self.run_vcs(
                "init", "--duration", "5-8", "--segment-range", "25-35",
                "--orientation", "landscape", "--out", str(out),
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            config = json.loads((out / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(config["duration_mode"], "range")
            self.assertEqual((config["duration_min"], config["duration_max"]), (5.0, 8.0))
            self.assertEqual(config["segment_seconds"], [25, 35])
            self.assertEqual((config["width"], config["height"]), (1920, 1080))

            proc = self.run_vcs("config", "--project", str(out), "--duration", "unlimited")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            config = json.loads((out / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(config["duration_mode"], "unlimited")

    def test_text_fallback(self) -> None:
        calls: list[str] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("content-length", "0"))
                self.rfile.read(length)
                calls.append(self.path)
                if self.path.startswith("/bad"):
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(b"quota exhausted")
                    return
                body = "# cleaned\n\n" + ("fallback text. " * 80)
                payload = json.dumps({"choices": [{"message": {"content": body}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args: object) -> None:
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory(prefix="vcs-text-") as tmp:
                out = Path(tmp) / "project"
                proc = self.run_vcs("init", "--duration", "1", "--out", str(out))
                self.assertEqual(proc.returncode, 0, proc.stderr)
                (out / "01_transcript.raw.txt").write_text("raw text. " * 200, encoding="utf-8")
                port = server.server_address[1]
                providers = {
                    "text": [
                        {"name": "bad", "provider": "openai", "base_url": f"http://127.0.0.1:{port}/bad", "api_key": "x", "model": "m"},
                        {"name": "good", "provider": "openai", "base_url": f"http://127.0.0.1:{port}/good", "api_key": "x", "model": "m"},
                    ]
                }
                (out / "providers.json").write_text(json.dumps(providers), encoding="utf-8")
                proc = self.run_vcs("text", "--project", str(out), "--stage", "cleanup")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertTrue((out / "02_transcript.md").exists())
                self.assertEqual(calls[0], "/bad/v1/chat/completions")
                self.assertEqual(calls[1], "/good/v1/chat/completions")
        finally:
            server.shutdown()
            server.server_close()

    def test_auto_folder_and_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vcs-folder-") as tmp:
            proc = subprocess.run(
                [
                    sys.executable, str(VCS), "run", "--mock",
                    "--duration", "0.1", "--segment", "10", "--segment-range", "5-15",
                ],
                capture_output=True, text=True, timeout=180, cwd=tmp,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            folders = [p for p in (Path(tmp) / "projects").iterdir() if p.is_dir()]
            self.assertEqual(len(folders), 1)
            folder = folders[0]
            self.assertTrue(folder.name.startswith("Mock_"))
            self.assertIn("测试视频", folder.name)
            self.assertFalse((folder / "audio").exists())
            self.assertFalse((folder / "clips").exists())
            self.assertFalse((folder / "logs").exists())
            self.assertFalse((folder / "final").exists())
            finals = list(folder.glob("07_*.mp4"))
            self.assertEqual(len(finals), 1)
            metadata = json.loads((folder / "04_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["source"]["type"], "text")

    def test_source_folder_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vcs-names-") as tmp:
            pdf = Path(tmp) / "sample.pdf"
            pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
            cases = [
                ("https://www.youtube.com/watch?v=x", "YouTube_"),
                ("https://www.bloomberg.com/news/articles/x", "bloomberg.com_"),
                (str(pdf), "PDF_"),
            ]
            for input_value, prefix in cases:
                proc = subprocess.run(
                    [sys.executable, str(VCS), "init", "--input", input_value],
                    capture_output=True, text=True, timeout=60, cwd=tmp,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
            names = sorted(path.name for path in (Path(tmp) / "projects").iterdir())
            self.assertEqual(len(names), 3)
            self.assertTrue(any(name.startswith("YouTube_") for name in names), names)
            self.assertTrue(any(name.startswith("bloomberg.com_") for name in names), names)
            self.assertTrue(any(name.startswith("PDF_") for name in names), names)


if __name__ == "__main__":
    unittest.main()
