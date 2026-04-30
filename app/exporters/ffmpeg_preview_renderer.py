from __future__ import annotations

import json
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
        self.ffmpeg_path = ffmpeg_path

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
            "mode": "fallback_black_video_with_sidecar_srt",
        }
        (preview_dir / "preview_render_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise RuntimeError(f"ffmpeg preview render failed: {completed.stderr}")
        return result

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
            raise FileNotFoundError("ffmpeg executable not found. Add ffmpeg to PATH or pass --ffmpeg.") from exc
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
