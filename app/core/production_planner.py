from __future__ import annotations

import re
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
            location_desc = self._clean_location(str(scene.get("location", {}).get("description", "")))
            emotion = self._primary_emotion(scene)
            source_text = self._clean_sentence(str(scene.get("source_text", "")))
            for keyframe in scene.get("keyframes", []):
                keyframe_id = str(keyframe.get("keyframe_id", "kf"))
                keyframe_desc = self._clean_keyframe_description(str(keyframe.get("description", "")))
                focus_text = self._focus_text_for_keyframe(keyframe_id, keyframe_desc, source_text)
                prompt_text = self._compose_keyframe_prompt(
                    title=title,
                    style_ref=style_ref,
                    location_desc=location_desc,
                    emotion=emotion,
                    focus_text=focus_text,
                )
                prompts.append(
                    {
                        "prompt_id": f"{scene_id}_{keyframe_id}",
                        "scene_id": scene_id,
                        "scene_title": title,
                        "keyframe_id": keyframe_id,
                        "time_sec": keyframe.get("time_sec", 0),
                        "style_ref": style_ref,
                        "visual_focus": focus_text,
                        "location": location_desc,
                        "emotion": emotion,
                        "prompt": prompt_text,
                        "negative_prompt": self._negative_prompt(),
                        "quality_score": self._prompt_quality_score(prompt_text),
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
        focus_text: str,
    ) -> str:
        return (
            f"Style: {style_ref}. "
            f"Scene: {title}. "
            f"Visual focus: {focus_text}. "
            f"Location: {location_desc}. "
            f"Character emotion: {emotion}. "
            "Cinematic composition, consistent character design, coherent lighting, production-ready keyframe."
        )

    def _focus_text_for_keyframe(self, keyframe_id: str, keyframe_desc: str, source_text: str) -> str:
        cleaned_desc = self._clean_sentence(keyframe_desc)
        if keyframe_id == "mid" and "중간 핵심 이미지" in cleaned_desc:
            return self._middle_phrase(source_text)
        if not cleaned_desc:
            return self._middle_phrase(source_text)
        return self._limit_text(cleaned_desc, 160)

    def _clean_keyframe_description(self, text: str) -> str:
        cleaned = self._clean_sentence(text)
        cleaned = re.sub(r"^[^:：]{1,40}[:：]\s*", "", cleaned)
        return cleaned

    def _clean_location(self, text: str) -> str:
        cleaned = self._clean_sentence(text)
        if "project_bible.location_defaults" in cleaned:
            return "이전 장면과 연결되는 봉인실 또는 핵심 사건 장소"
        return cleaned.rstrip(".")

    def _clean_sentence(self, text: str) -> str:
        cleaned = " ".join(text.split())
        cleaned = re.sub(r"\s+([.,!?。！？])", r"\1", cleaned)
        cleaned = re.sub(r"([.,!?。！？]){2,}", r"\1", cleaned)
        cleaned = re.sub(r"\.\s*\.", ".", cleaned)
        return cleaned.strip()

    def _middle_phrase(self, source_text: str) -> str:
        cleaned = self._clean_sentence(source_text)
        if len(cleaned) <= 160:
            return cleaned
        midpoint = len(cleaned) // 2
        start = max(0, midpoint - 80)
        end = min(len(cleaned), midpoint + 80)
        return self._trim_to_word_boundary(cleaned[start:end])

    def _limit_text(self, text: str, max_length: int) -> str:
        cleaned = self._clean_sentence(text)
        if len(cleaned) <= max_length:
            return cleaned
        return self._trim_to_word_boundary(cleaned[:max_length])

    def _trim_to_word_boundary(self, text: str) -> str:
        trimmed = text.strip()
        if " " in trimmed:
            last_space = trimmed.rfind(" ")
            if last_space >= max(20, len(trimmed) - 20):
                trimmed = trimmed[:last_space]
        return trimmed.rstrip(" ,.;:。！？!")

    def _prompt_quality_score(self, prompt: str) -> float:
        score = 75.0
        if "project_bible.location_defaults" not in prompt:
            score += 10.0
        if ".." not in prompt:
            score += 5.0
        if len(prompt) <= 520:
            score += 5.0
        if "Visual focus:" in prompt and "Location:" in prompt:
            score += 5.0
        return min(100.0, round(score, 2))

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
