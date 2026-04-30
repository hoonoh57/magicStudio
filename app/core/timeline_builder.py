from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.core.models import write_json_file


class TimelineBuilder:
    """Build internal timeline.json from VML scenes."""

    def build(self, vml_episode: Dict[str, Any]) -> Dict[str, Any]:
        current = 0.0
        video_clips: List[Dict[str, Any]] = []
        narration_clips: List[Dict[str, Any]] = []
        subtitle_clips: List[Dict[str, Any]] = []
        music_clips: List[Dict[str, Any]] = []

        for scene in vml_episode.get("scenes", []):
            duration = float(scene.get("duration_sec", 0.0))
            scene_id = str(scene.get("scene_id", ""))
            title = str(scene.get("title", ""))
            video_clips.append(
                {
                    "clip_id": f"{scene_id}_video",
                    "scene_id": scene_id,
                    "source": f"keyframes/{scene_id}_start.png",
                    "start_sec": round(current, 3),
                    "duration_sec": duration,
                    "effect": "slow_push_in",
                    "title": title,
                }
            )
            narration = scene.get("narration", {})
            narration_text = str(narration.get("text", ""))
            narration_clips.append(
                {
                    "clip_id": f"{scene_id}_narration",
                    "scene_id": scene_id,
                    "source": f"audio/{scene_id}_narration.wav",
                    "script": narration_text,
                    "start_sec": round(current, 3),
                    "duration_sec": duration,
                }
            )
            subtitle_clips.append(
                {
                    "clip_id": f"{scene_id}_subtitle",
                    "scene_id": scene_id,
                    "text": narration_text,
                    "start_sec": round(current, 3),
                    "end_sec": round(current + duration, 3),
                }
            )
            music_clips.append(
                {
                    "clip_id": f"{scene_id}_bgm",
                    "scene_id": scene_id,
                    "cue": scene.get("audio", {}).get("bgm", "music_profile.base"),
                    "start_sec": round(current, 3),
                    "duration_sec": duration,
                }
            )
            current += duration

        return {
            "timeline_version": "0.1",
            "project_id": vml_episode.get("project_id", ""),
            "title": vml_episode.get("title", ""),
            "fps": 24,
            "resolution": "1920x1080",
            "duration_sec": round(current, 3),
            "tracks": [
                {"track_id": "V1", "type": "video", "clips": video_clips},
                {"track_id": "A1_NARRATION", "type": "audio", "clips": narration_clips},
                {"track_id": "A2_MUSIC", "type": "audio", "clips": music_clips},
                {"track_id": "S1", "type": "subtitle", "clips": subtitle_clips},
            ],
        }

    def build_and_save(self, vml_episode: Dict[str, Any], output_path: Path | str) -> Dict[str, Any]:
        timeline = self.build(vml_episode)
        write_json_file(Path(output_path), timeline)
        return timeline
