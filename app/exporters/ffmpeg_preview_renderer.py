from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


class FfmpegPreviewRenderer:
    """Render a local-only MVP preview video from preview_render_plan.json.

    This renderer intentionally has no third-party Python dependency. The first
    implementation creates a black-background timing preview with silent audio
    and copies captions as a sidecar SRT. Later versions can consume generated
    keyframe images, narration WAV files, and burn-in subtitles.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        self.ffmpeg_path = self._resolve_ffmpeg(ffmpeg_path)

    def render_from_file(self, episode_dir: Path | str, plan_file: str = "preview_render_plan.json") -> Dict[str, Any]:
        root = Path(episode_dir)
        plan_path = root / plan_file
        if not plan_path.exists():
            raise FileNotFoundError(f"preview render plan not found: {plan_path}")
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        return self.render(root, plan)

    def render(self, episode_dir: Path, plan: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_ffmpeg()

        preview_dir = episode_dir / "preview"
        preview_dir.mkdir(parents=True, exist_ok=True)

        output_path = episode_dir / str(plan.get("output", "preview/preview.mp4"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        duration = float(plan.get("duration_sec", 0.0))
        if duration <= 0:
            raise ValueError("preview duration_sec must be greater than zero")

        resolution = str(plan.get("resolution", "1920x1080"))
        fps = int(plan.get("fps", 24))
        captions_name = str(plan.get("captions", "captions.srt"))
        captions_source = episode_dir / captions_name
        captions_sidecar = output_path.with_suffix(".srt")
        if captions_source.exists():
            shutil.copyfile(captions_source, captions_sidecar)

        scene_manifest_path = preview_dir / "preview_scene_manifest.json"
        self._write_scene_manifest(plan, scene_manifest_path)

        command = self._build_fallback_command(
            output_path=output_path,
            duration=duration,
            resolution=resolution,
            fps=fps,
        )

        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        result = {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "command": command,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "output_path": str(output_path),
            "captions_sidecar": str(captions_sidecar) if captions_source.exists() else "",
            "scene_manifest": str(scene_manifest_path),
            "ffmpeg_path": self.ffmpeg_path,
            "mode": "fallback_black_video_with_sidecar_srt",
        }
        (preview_dir / "preview_render_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise RuntimeError(f"ffmpeg preview render failed: {completed.stderr}")
        return result

    def _resolve_ffmpeg(self, ffmpeg_path: str) -> str:
        explicit = ffmpeg_path.strip().strip('"')
        if explicit and explicit.lower() != "ffmpeg":
            path = Path(explicit)
            if path.exists():
                return str(path)
            found = shutil.which(explicit)
            if found:
                return found
            return explicit

        env_path = os.environ.get("FFMPEG_PATH", "").strip().strip('"')
        if env_path:
            path = Path(env_path)
            if path.exists():
                return str(path)

        found = shutil.which("ffmpeg")
        if found:
            return found

        candidates = self._candidate_ffmpeg_paths()
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return explicit or "ffmpeg"

    def _candidate_ffmpeg_paths(self) -> List[Path]:
        cwd = Path.cwd()
        home = Path.home()
        candidates = [
            cwd / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe",
            cwd / "ffmpeg" / "bin" / "ffmpeg.exe",
            cwd / "bin" / "ffmpeg.exe",
            Path("C:/ffmpeg/bin/ffmpeg.exe"),
            Path("C:/ProgramData/chocolatey/bin/ffmpeg.exe"),
            home / "scoop" / "shims" / "ffmpeg.exe",
            home / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe",
        ]
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            candidates.append(Path(local_app_data) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe")
        return candidates

    def _ensure_ffmpeg(self) -> None:
        try:
            completed = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            searched = [str(path) for path in self._candidate_ffmpeg_paths()]
            message = (
                "ffmpeg executable not found. "
                "Install FFmpeg, set FFMPEG_PATH, put ffmpeg.exe under tools/ffmpeg/bin, "
                "or pass --ffmpeg C:\\path\\to\\ffmpeg.exe. "
                f"Resolved value: {self.ffmpeg_path}. Searched: {searched}"
            )
            raise FileNotFoundError(message) from exc
        if completed.returncode != 0:
            raise RuntimeError(f"ffmpeg check failed: {completed.stderr}")

    def _build_fallback_command(self, output_path: Path, duration: float, resolution: str, fps: int) -> List[str]:
        return [
            self.ffmpeg_path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s={resolution}:r={fps}:d={duration}",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

    def _write_scene_manifest(self, plan: Dict[str, Any], output_path: Path) -> None:
        manifest = {
            "version": plan.get("version", "0.1"),
            "title": plan.get("title", ""),
            "duration_sec": plan.get("duration_sec", 0),
            "scenes": [],
        }
        for scene in plan.get("scenes", []):
            manifest["scenes"].append(
                {
                    "scene_id": scene.get("scene_id", ""),
                    "title": scene.get("title", ""),
                    "start_sec": scene.get("start_sec", 0),
                    "duration_sec": scene.get("duration_sec", 0),
                    "narration_text": scene.get("narration", {}).get("text", ""),
                    "image_slots": scene.get("image_slots", []),
                }
            )
        output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
