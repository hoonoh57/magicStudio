from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.core.models import write_json_file


class PreviewRenderPlanner:
    """Create a local-only preview render plan from timeline and production files.

    This plan is intentionally provider-neutral. It can be consumed by an FFmpeg
    renderer, a GUI preview player, or an external editing exporter.
    """

    def build(
        self,
        timeline: Dict[str, Any],
        keyframe_prompts: Dict[str, Any],
        tts_script: Dict[str, Any],
        captions_path: str = "captions.srt",
    ) -> Dict[str, Any]:
        prompt_map = self._prompt_map(keyframe_prompts)
        narration_map = self._narration_map(tts_script)
        scenes: List[Dict[str, Any]] = []

        for clip in self._video_clips(timeline):
            scene_id = str(clip.get("scene_id", ""))
            start_prompt = prompt_map.get((scene_id, "start"), {})
            mid_prompt = prompt_map.get((scene_id, "mid"), {})
            end_prompt = prompt_map.get((scene_id, "end"), {})
            narration = narration_map.get(scene_id, {})
            scenes.append(
                {
                    "scene_id": scene_id,
                    "title": clip.get("title", ""),
                    "start_sec": clip.get("start_sec", 0),
                    "duration_sec": clip.get("duration_sec", 0),
                    "image_slots": [
                        self._image_slot(scene_id, "start", start_prompt, 0.0),
                        self._image_slot(scene_id, "mid", mid_prompt, 0.5),
                        self._image_slot(scene_id, "end", end_prompt, 1.0),
                    ],
                    "narration": {
                        "text": narration.get("text", ""),
                        "expected_audio": f"audio/{scene_id}_narration.wav",
                        "tts_ref": narration.get("tts_ref", "narration"),
                        "emotion": narration.get("emotion", "neutral"),
                    },
                    "fallback_visual": {
                        "mode": "title_card",
                        "background": "black",
                        "text": clip.get("title", scene_id),
                    },
                }
            )

        return {
            "version": "0.1",
            "project_id": timeline.get("project_id", ""),
            "title": timeline.get("title", ""),
            "duration_sec": timeline.get("duration_sec", 0),
            "resolution": timeline.get("resolution", "1920x1080"),
            "fps": timeline.get("fps", 24),
            "captions": captions_path,
            "output": "preview/preview.mp4",
            "render_modes": [
                "fallback_title_cards",
                "image_slots_if_available",
                "narration_audio_if_available",
                "caption_burn_in_optional",
            ],
            "scenes": scenes,
            "local_only_policy": "Preview media is created under local_projects/<project>/ and ignored by git.",
        }

    def build_and_save(
        self,
        timeline: Dict[str, Any],
        keyframe_prompts: Dict[str, Any],
        tts_script: Dict[str, Any],
        episode_dir: Path | str,
    ) -> Dict[str, Any]:
        root = Path(episode_dir)
        plan = self.build(
            timeline=timeline,
            keyframe_prompts=keyframe_prompts,
            tts_script=tts_script,
            captions_path="captions.srt",
        )
        write_json_file(root / "preview_render_plan.json", plan)
        return plan

    def _video_clips(self, timeline: Dict[str, Any]) -> List[Dict[str, Any]]:
        for track in timeline.get("tracks", []):
            if track.get("type") == "video":
                clips = track.get("clips", [])
                if isinstance(clips, list):
                    return clips
        return []

    def _prompt_map(self, keyframe_prompts: Dict[str, Any]) -> Dict[tuple[str, str], Dict[str, Any]]:
        result: Dict[tuple[str, str], Dict[str, Any]] = {}
        for prompt in keyframe_prompts.get("prompts", []):
            scene_id = str(prompt.get("scene_id", ""))
            keyframe_id = str(prompt.get("keyframe_id", ""))
            result[(scene_id, keyframe_id)] = prompt
        return result

    def _narration_map(self, tts_script: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for cue in tts_script.get("cues", []):
            scene_id = str(cue.get("scene_id", ""))
            result[scene_id] = cue
        return result

    def _image_slot(
        self,
        scene_id: str,
        keyframe_id: str,
        prompt: Dict[str, Any],
        relative_time: float,
    ) -> Dict[str, Any]:
        return {
            "slot_id": f"{scene_id}_{keyframe_id}",
            "keyframe_id": keyframe_id,
            "relative_time": relative_time,
            "expected_image": f"keyframes/{scene_id}_{keyframe_id}.png",
            "visual_focus": prompt.get("visual_focus", ""),
            "shot_type": prompt.get("shot_type", "keyframe"),
            "prompt_ref": prompt.get("prompt_id", ""),
        }
