from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


class FfmpegPreviewRenderer:
    """Render a local-only MVP preview video from preview_render_plan.json.

    The renderer supports three modes:
    1. image_slide_preview_with_sidecar_srt when local keyframe images exist.
    2. generated_placeholder_slide_preview when no keyframe image exists.
    3. fallback_black_video_with_sidecar_srt if placeholder generation is disabled.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg", generate_placeholders: bool = True) -> None:
        self.ffmpeg_path = self._resolve_ffmpeg(ffmpeg_path)
        self.generate_placeholders = generate_placeholders

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

        image_items = self._collect_existing_image_items(episode_dir, plan)
        generated_placeholder_count = 0
        if not image_items and self.generate_placeholders:
            generated_placeholder_count = self._generate_placeholder_keyframes(episode_dir, plan, resolution)
            image_items = self._collect_existing_image_items(episode_dir, plan)

        image_concat_path = preview_dir / "preview_image_concat.txt"

        if image_items:
            self._write_image_concat_file(image_items, image_concat_path)
            command = self._build_image_slide_command(
                concat_file=image_concat_path,
                output_path=output_path,
                resolution=resolution,
                fps=fps,
            )
            if generated_placeholder_count > 0:
                mode = "generated_placeholder_slide_preview"
            else:
                mode = "image_slide_preview_with_sidecar_srt"
        else:
            command = self._build_fallback_command(
                output_path=output_path,
                duration=duration,
                resolution=resolution,
                fps=fps,
            )
            mode = "fallback_black_video_with_sidecar_srt"

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
            "mode": mode,
            "used_image_count": len(image_items),
            "generated_placeholder_count": generated_placeholder_count,
            "image_concat_file": str(image_concat_path) if image_items else "",
            "used_images": [str(item["image_path"]) for item in image_items],
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
            Path("E:/ffmpeg/bin/ffmpeg.exe"),
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

    def _build_image_slide_command(self, concat_file: Path, output_path: Path, resolution: str, fps: int) -> List[str]:
        scale_pad = (
            f"scale={resolution}:force_original_aspect_ratio=decrease,"
            f"pad={resolution}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}"
        )
        return [
            self.ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-vf",
            scale_pad,
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

    def _build_placeholder_image_command(
        self,
        output_path: Path,
        resolution: str,
        title: str,
        focus: str,
        shot_type: str,
    ) -> List[str]:
        text = self._placeholder_text(title, focus, shot_type)
        draw_text = self._escape_drawtext(text)
        filter_text = (
            f"color=c=#101018:s={resolution}:d=1,"
            f"drawtext=text='{draw_text}':fontcolor=white:fontsize=44:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.45:boxborderw=24"
        )
        return [
            self.ffmpeg_path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            filter_text,
            "-frames:v",
            "1",
            str(output_path),
        ]

    def _collect_existing_image_items(self, episode_dir: Path, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for scene in plan.get("scenes", []):
            scene_duration = float(scene.get("duration_sec", 0.0))
            slot_duration = max(1.0, scene_duration / 3.0)
            for slot in scene.get("image_slots", []):
                rel_path = str(slot.get("expected_image", ""))
                if not rel_path:
                    continue
                image_path = episode_dir / rel_path
                if image_path.exists():
                    items.append(
                        {
                            "image_path": image_path,
                            "duration_sec": slot_duration,
                            "scene_id": scene.get("scene_id", ""),
                            "slot_id": slot.get("slot_id", ""),
                        }
                    )
        return items

    def _generate_placeholder_keyframes(self, episode_dir: Path, plan: Dict[str, Any], resolution: str) -> int:
        count = 0
        for scene in plan.get("scenes", []):
            title = str(scene.get("title", ""))
            for slot in scene.get("image_slots", []):
                rel_path = str(slot.get("expected_image", ""))
                if not rel_path:
                    continue
                output_path = episode_dir / rel_path
                if output_path.exists():
                    continue
                output_path.parent.mkdir(parents=True, exist_ok=True)
                command = self._build_placeholder_image_command(
                    output_path=output_path,
                    resolution=resolution,
                    title=title,
                    focus=str(slot.get("visual_focus", "")),
                    shot_type=str(slot.get("shot_type", "keyframe")),
                )
                completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
                if completed.returncode == 0 and output_path.exists():
                    count += 1
        return count

    def _write_image_concat_file(self, image_items: List[Dict[str, Any]], output_path: Path) -> None:
        lines: List[str] = []
        for item in image_items:
            image_path = Path(item["image_path"]).resolve()
            escaped = str(image_path).replace("'", "'\\''")
            lines.append(f"file '{escaped}'")
            lines.append(f"duration {float(item['duration_sec']):.3f}")
        if image_items:
            last_path = Path(image_items[-1]["image_path"]).resolve()
            escaped_last = str(last_path).replace("'", "'\\''")
            lines.append(f"file '{escaped_last}'")
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

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

    def _placeholder_text(self, title: str, focus: str, shot_type: str) -> str:
        merged = f"{title}\n{shot_type}\n{focus}".strip()
        merged = " ".join(merged.split())
        if len(merged) > 160:
            merged = merged[:157] + "..."
        return merged

    def _escape_drawtext(self, text: str) -> str:
        escaped = text.replace("\\", "\\\\")
        escaped = escaped.replace(":", "\\:")
        escaped = escaped.replace("'", "\\'")
        escaped = escaped.replace("%", "\\%")
        escaped = escaped.replace("\n", "\\n")
        return escaped
