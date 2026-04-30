from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.core.models import write_json_file


class ProductionPlanner:
    """Derive production-ready files from VML.

    The planner does not generate final media. It creates deterministic plans that
    image, audio, TTS, and editor providers can consume.
    """

    def build_keyframe_prompts(self, vml_episode: Dict[str, Any]) -> Dict[str, Any]:
        prompts: List[Dict[str, Any]] = []
        for scene in vml_episode.get("scenes", []):
            scene_id = str(scene.get("scene_id", ""))
            title = str(scene.get("title", ""))
            style_ref = str(scene.get("style_ref", "general_cinematic_story"))
            location_desc = str(scene.get("location", {}).get("description", ""))
            emotion = self._primary_emotion(scene)
            for keyframe in scene.get("keyframes", []):
                prompt_text = self._compose_keyframe_prompt(
                    title=title,
                    style_ref=style_ref,
                    location_desc=location_desc,
                    emotion=emotion,
                    keyframe_desc=str(keyframe.get("description", "")),
                )
                prompts.append(
                    {
                        "prompt_id": f"{scene_id}_{keyframe.get('keyframe_id', 'kf')}",
                        "scene_id": scene_id,
                        "scene_title": title,
                        "keyframe_id": keyframe.get("keyframe_id", ""),
                        "time_sec": keyframe.get("time_sec", 0),
                        "style_ref": style_ref,
                        "prompt": prompt_text,
                        "negative_prompt": self._negative_prompt(),
                        "local_asset_policy": "generated image should be stored under local_projects/<project>/assets/generated and ignored by git",
                    }
                )
        return {
            "version": "0.1",
            "project_id": vml_episode.get("project_id", ""),
            "title": vml_episode.get("title", ""),
            "prompts": prompts,
        }

    def build_tts_script(self, vml_episode: Dict[str, Any]) -> Dict[str, Any]:
        cues: List[Dict[str, Any]] = []
        current = 0.0
        for scene in vml_episode.get("scenes", []):
            duration = float(scene.get("duration_sec", 0.0))
            narration = scene.get("narration", {})
            text = str(narration.get("text", "")).strip()
            if text:
                cues.append(
                    {
                        "cue_id": f"{scene.get('scene_id', '')}_narration",
                        "scene_id": scene.get("scene_id", ""),
                        "scene_title": scene.get("title", ""),
                        "speaker": "narrator",
                        "tts_ref": narration.get("tts_ref", "narration"),
                        "text": text,
                        "start_sec": round(current, 3),
                        "duration_sec": duration,
                        "emotion": self._primary_emotion(scene),
                        "quality_score": narration.get("quality_score", 0),
                    }
                )
            current += duration
        return {
            "version": "0.1",
            "project_id": vml_episode.get("project_id", ""),
            "title": vml_episode.get("title", ""),
            "cues": cues,
        }

    def build_music_plan(self, vml_episode: Dict[str, Any]) -> Dict[str, Any]:
        cues: List[Dict[str, Any]] = []
        current = 0.0
        for scene in vml_episode.get("scenes", []):
            duration = float(scene.get("duration_sec", 0.0))
            cues.append(
                {
                    "cue_id": f"{scene.get('scene_id', '')}_music",
                    "scene_id": scene.get("scene_id", ""),
                    "scene_title": scene.get("title", ""),
                    "start_sec": round(current, 3),
                    "duration_sec": duration,
                    "bgm_cue": scene.get("audio", {}).get("bgm", "subtle cinematic bed"),
                    "mix_note": "Narration must remain clear; keep BGM below dialogue.",
                }
            )
            current += duration
        return {
            "version": "0.1",
            "project_id": vml_episode.get("project_id", ""),
            "title": vml_episode.get("title", ""),
            "cues": cues,
        }

    def build_sfx_plan(self, vml_episode: Dict[str, Any]) -> Dict[str, Any]:
        cues: List[Dict[str, Any]] = []
        current = 0.0
        for scene in vml_episode.get("scenes", []):
            duration = float(scene.get("duration_sec", 0.0))
            sfx_items = scene.get("audio", {}).get("sfx", [])
            if isinstance(sfx_items, list):
                for index, cue in enumerate(sfx_items):
                    cues.append(
                        {
                            "cue_id": f"{scene.get('scene_id', '')}_sfx_{index + 1:02d}",
                            "scene_id": scene.get("scene_id", ""),
                            "scene_title": scene.get("title", ""),
                            "sfx_cue": cue,
                            "start_sec": round(current + min(duration * 0.15 * (index + 1), max(duration - 1.0, 0.0)), 3),
                            "duration_sec": 1.5,
                            "mix_note": "Place as subtle scene texture unless marked as impact.",
                        }
                    )
            current += duration
        return {
            "version": "0.1",
            "project_id": vml_episode.get("project_id", ""),
            "title": vml_episode.get("title", ""),
            "cues": cues,
        }

    def build_export_package(
        self,
        vml_episode: Dict[str, Any],
        timeline: Dict[str, Any],
        relative_files: Dict[str, str],
    ) -> Dict[str, Any]:
        return {
            "version": "0.1",
            "project_id": vml_episode.get("project_id", ""),
            "title": vml_episode.get("title", ""),
            "duration_sec": timeline.get("duration_sec", 0),
            "scene_count": len(vml_episode.get("scenes", [])),
            "files": relative_files,
            "local_only_policy": [
                "User scenarios, images, videos, audio, motions, poses, sprites, renders, and exports stay local.",
                "Only source code, schemas, templates, and safe profiles are tracked by git.",
            ],
            "next_steps": [
                "Review VML and narration quality_score.",
                "Generate or register keyframe images from keyframe_prompts.json.",
                "Generate or register TTS audio from tts_script.json.",
                "Open timeline.json in an editor/exporter pipeline.",
            ],
        }

    def save_all(
        self,
        vml_episode: Dict[str, Any],
        timeline: Dict[str, Any],
        episode_dir: Path | str,
    ) -> Dict[str, Path]:
        root = Path(episode_dir)
        keyframe_path = root / "keyframe_prompts.json"
        tts_path = root / "tts_script.json"
        music_path = root / "music_plan.json"
        sfx_path = root / "sfx_plan.json"
        export_path = root / "export_package.json"

        write_json_file(keyframe_path, self.build_keyframe_prompts(vml_episode))
        write_json_file(tts_path, self.build_tts_script(vml_episode))
        write_json_file(music_path, self.build_music_plan(vml_episode))
        write_json_file(sfx_path, self.build_sfx_plan(vml_episode))

        relative_files = {
            "vml": "vml_scenes.json",
            "timeline": "timeline.json",
            "captions": "captions.srt",
            "keyframe_prompts": "keyframe_prompts.json",
            "tts_script": "tts_script.json",
            "music_plan": "music_plan.json",
            "sfx_plan": "sfx_plan.json",
        }
        write_json_file(export_path, self.build_export_package(vml_episode, timeline, relative_files))
        return {
            "keyframe_prompts": keyframe_path,
            "tts_script": tts_path,
            "music_plan": music_path,
            "sfx_plan": sfx_path,
            "export_package": export_path,
        }

    def _compose_keyframe_prompt(
        self,
        title: str,
        style_ref: str,
        location_desc: str,
        emotion: str,
        keyframe_desc: str,
    ) -> str:
        return (
            f"{style_ref}. Scene: {title}. {keyframe_desc}. "
            f"Location: {location_desc}. Character emotion: {emotion}. "
            "Cinematic composition, consistent character design, coherent lighting, production-ready keyframe."
        )

    def _negative_prompt(self) -> str:
        return (
            "inconsistent face, random costume change, extra fingers, broken anatomy, unreadable text, "
            "overly cartoonish style, low resolution, noisy composition"
        )

    def _primary_emotion(self, scene: Dict[str, Any]) -> str:
        characters = scene.get("characters", [])
        if isinstance(characters, list) and characters:
            first = characters[0]
            if isinstance(first, dict):
                return str(first.get("emotion", "neutral"))
        return "neutral"
