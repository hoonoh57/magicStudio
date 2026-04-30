from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class FfmpegPreviewRenderer:
    """Render a local-only MVP preview video from preview_render_plan.json.

    The renderer supports three modes:
    1. image_slide_preview_with_sidecar_srt when local keyframe images exist.
    2. generated_placeholder_slide_preview when no keyframe image exists.
    3. fallback_black_video_with_sidecar_srt if placeholder generation is disabled.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg", generate_placeholders: bool = True, burn_subtitles: bool = False) -> None:
        self.ffmpeg_path = self._resolve_ffmpeg(ffmpeg_path)
        self.generate_placeholders = generate_placeholders
        self.burn_subtitles = burn_subtitles

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

        audio_result = self._build_preview_audio(episode_dir, plan, preview_dir)
        audio_input_path = str(audio_result.get("audio_path", ""))
        image_concat_path = preview_dir / "preview_image_concat.txt"
        subtitle_filter = self._subtitle_filter(captions_source, captions_sidecar)

        if image_items:
            self._write_image_concat_file(image_items, image_concat_path)
            command = self._build_image_slide_command(
                concat_file=image_concat_path,
                output_path=output_path,
                resolution=resolution,
                fps=fps,
                subtitle_filter=subtitle_filter,
                audio_input_path=audio_input_path,
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
                subtitle_filter=subtitle_filter,
                audio_input_path=audio_input_path,
            )
            mode = "fallback_black_video_with_sidecar_srt"

        if subtitle_filter:
            mode = mode + "_burned_subtitles"
        if audio_result.get("used_real_audio_count", 0) > 0:
            mode = mode + "_with_narration_audio"

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
            "burn_subtitles": bool(subtitle_filter),
            "used_image_count": len(image_items),
            "generated_placeholder_count": generated_placeholder_count,
            "image_concat_file": str(image_concat_path) if image_items else "",
            "used_images": [str(item["image_path"]) for item in image_items],
            "audio": audio_result,
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

    def _parse_resolution(self, resolution: str) -> Tuple[int, int]:
        value = resolution.lower().replace(" ", "")
        if "x" not in value:
            return 1920, 1080
        parts = value.split("x", 1)
        try:
            width = int(parts[0])
            height = int(parts[1])
        except ValueError:
            return 1920, 1080
        if width <= 0 or height <= 0:
            return 1920, 1080
        return width, height

    def _build_fallback_command(self, output_path: Path, duration: float, resolution: str, fps: int, subtitle_filter: str, audio_input_path: str) -> List[str]:
        vf = "drawbox=x=0:y=0:w=iw:h=ih:color=#2f80ed@0.40:t=36,drawbox=x=iw*0.08:y=ih*0.18:w=iw*0.84:h=ih*0.64:color=#ffffff@0.16:t=8"
        if subtitle_filter:
            vf = vf + "," + subtitle_filter
        command = [
            self.ffmpeg_path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=#101018:s={resolution}:r={fps}:d={duration}",
        ]
        if audio_input_path:
            command.extend(["-i", audio_input_path])
        else:
            command.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"])
        command.extend([
            "-vf",
            vf,
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
        ])
        return command

    def _build_image_slide_command(self, concat_file: Path, output_path: Path, resolution: str, fps: int, subtitle_filter: str, audio_input_path: str) -> List[str]:
        width, height = self._parse_resolution(resolution)
        scale_pad = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}"
        )
        vf = scale_pad
        if subtitle_filter:
            vf = vf + "," + subtitle_filter
        command = [
            self.ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
        ]
        if audio_input_path:
            command.extend(["-i", audio_input_path])
        else:
            command.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"])
        command.extend([
            "-vf",
            vf,
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
        ])
        return command

    def _build_placeholder_image_command(
        self,
        output_path: Path,
        resolution: str,
        title: str,
        focus: str,
        shot_type: str,
        color: str,
    ) -> List[str]:
        filter_text = (
            f"color=c=#101018:s={resolution}:d=1,"
            f"drawbox=x=0:y=0:w=iw:h=ih:color={color}@0.42:t=48,"
            f"drawbox=x=iw*0.08:y=ih*0.16:w=iw*0.84:h=ih*0.68:color=#ffffff@0.16:t=10,"
            f"drawbox=x=iw*0.12:y=ih*0.22:w=iw*0.76:h=ih*0.08:color={color}@0.70:t=fill,"
            f"drawbox=x=iw*0.12:y=ih*0.70:w=iw*0.76:h=ih*0.04:color={color}@0.50:t=fill"
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

    def _subtitle_filter(self, captions_source: Path, captions_sidecar: Path) -> str:
        if not self.burn_subtitles:
            return ""
        if not captions_source.exists():
            return ""
        subtitle_path = captions_sidecar if captions_sidecar.exists() else captions_source
        escaped = self._escape_subtitle_path(subtitle_path.resolve())
        style = "Fontsize=32,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=48"
        return f"subtitles='{escaped}':force_style='{style}'"

    def _escape_subtitle_path(self, path: Path) -> str:
        value = str(path).replace("\\", "/")
        value = value.replace(":", "\\:")
        value = value.replace("'", "\\'")
        return value

    def _build_preview_audio(self, episode_dir: Path, plan: Dict[str, Any], preview_dir: Path) -> Dict[str, Any]:
        segments_dir = preview_dir / "audio_segments"
        segments_dir.mkdir(parents=True, exist_ok=True)
        concat_path = preview_dir / "preview_audio_concat.txt"
        audio_path = preview_dir / "preview_audio.wav"
        scene_rows: List[Dict[str, Any]] = []
        concat_lines: List[str] = []
        used_real_audio_count = 0
        generated_silence_count = 0

        for index, scene in enumerate(plan.get("scenes", []), start=1):
            duration = float(scene.get("duration_sec", 0.0))
            if duration <= 0:
                continue
            scene_id = str(scene.get("scene_id", f"scene_{index}"))
            expected_audio = str(scene.get("narration", {}).get("expected_audio", ""))
            source_audio = episode_dir / expected_audio if expected_audio else Path("")
            segment_path = segments_dir / f"{index:03d}_{scene_id}.wav"
            if source_audio.exists() and source_audio.is_file():
                command = self._build_audio_segment_from_source_command(source_audio, segment_path, duration)
                used_real_audio_count += 1
                source_kind = "real_audio"
            else:
                command = self._build_silence_segment_command(segment_path, duration)
                generated_silence_count += 1
                source_kind = "generated_silence"
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if completed.returncode != 0:
                command = self._build_silence_segment_command(segment_path, duration)
                completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
                source_kind = "generated_silence_after_audio_failure"
            if completed.returncode == 0 and segment_path.exists():
                escaped = str(segment_path.resolve()).replace("'", "'\\''")
                concat_lines.append(f"file '{escaped}'")
                scene_rows.append({
                    "scene_id": scene_id,
                    "source_kind": source_kind,
                    "expected_audio": expected_audio,
                    "segment_path": str(segment_path),
                    "duration_sec": duration,
                })

        if not concat_lines:
            return {
                "audio_path": "",
                "used_real_audio_count": 0,
                "generated_silence_count": 0,
                "segments": [],
            }

        concat_path.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
        command = [
            self.ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c",
            "copy",
            str(audio_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if completed.returncode != 0 or not audio_path.exists():
            return {
                "audio_path": "",
                "used_real_audio_count": used_real_audio_count,
                "generated_silence_count": generated_silence_count,
                "segments": scene_rows,
                "error": completed.stderr,
            }
        return {
            "audio_path": str(audio_path),
            "concat_file": str(concat_path),
            "used_real_audio_count": used_real_audio_count,
            "generated_silence_count": generated_silence_count,
            "segments": scene_rows,
        }

    def _build_audio_segment_from_source_command(self, source_audio: Path, segment_path: Path, duration: float) -> List[str]:
        return [
            self.ffmpeg_path,
            "-y",
            "-i",
            str(source_audio),
            "-t",
            f"{duration:.3f}",
            "-af",
            "apad,aresample=48000",
            "-ac",
            "2",
            "-ar",
            "48000",
            str(segment_path),
        ]

    def _build_silence_segment_command(self, segment_path: Path, duration: float) -> List[str]:
        return [
            self.ffmpeg_path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t",
            f"{duration:.3f}",
            "-ac",
            "2",
            "-ar",
            "48000",
            str(segment_path),
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
        slot_counter = 0
        for scene in plan.get("scenes", []):
            for slot in scene.get("image_slots", []):
                rel_path = str(slot.get("expected_image", ""))
                if not rel_path:
                    continue
                output_path = episode_dir / rel_path
                if output_path.exists() and output_path.stat().st_size > 0:
                    continue
                output_path.parent.mkdir(parents=True, exist_ok=True)
                color = self._placeholder_color(slot_counter)
                slot_counter += 1
                command = self._build_placeholder_image_command(
                    output_path=output_path,
                    resolution=resolution,
                    title=str(scene.get("title", "")),
                    focus=str(slot.get("visual_focus", "")),
                    shot_type=str(slot.get("shot_type", "keyframe")),
                    color=color,
                )
                completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
                if completed.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
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

    def _placeholder_color(self, index: int) -> str:
        colors = [
            "#2f80ed",
            "#9b51e0",
            "#eb5757",
            "#27ae60",
            "#f2994a",
            "#56ccf2",
            "#bb6bd9",
            "#219653",
            "#f2c94c",
            "#2d9cdb",
            "#6fcf97",
            "#f26b6b",
        ]
        return colors[index % len(colors)]
