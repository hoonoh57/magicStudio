from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from app.core.models import Scene, write_json_file


class VmlEngine:
    """Convert key scenes into VML production commands."""

    def generate_scene_vml(self, scene: Scene, project_bible: Dict[str, Any]) -> Dict[str, Any]:
        motifs = project_bible.get("motifs", [])
        visual_style = project_bible.get("visual_style", {})
        vml: Dict[str, Any] = {
            "vml_version": "0.1",
            "scene_id": scene.scene_id,
            "scene_no": scene.scene_no,
            "title": scene.title,
            "purpose": scene.dramatic_function,
            "duration_sec": scene.duration_sec,
            "style_ref": visual_style.get("style_name", "general_cinematic_story"),
            "motifs": motifs,
            "location": {
                "location_ref": "primary_location",
                "description": "project_bible.location_defaults.primary_location을 기준으로 구체화한다.",
            },
            "characters": [
                {
                    "character_ref": "main_character",
                    "emotion": self._emotion_for_scene(scene),
                    "position": "center_or_front",
                    "consistency_required": True,
                }
            ],
            "camera": self._camera_plan(scene),
            "motion": [],
            "dialogue": [],
            "narration": {
                "text": self._narration_stub(scene),
                "tts_ref": "narration",
            },
            "audio": {
                "bgm": "music_profile.base",
                "sfx": [],
            },
            "subtitle": {
                "enabled": True,
                "source": "narration_and_dialogue",
            },
            "keyframes": self._keyframes(scene),
            "review_checks": [
                "캐릭터 일관성 확인",
                "장면 목적이 선명한지 확인",
                "다음 장면과 연결되는 후킹 확인",
            ],
        }
        return vml

    def generate_episode_vml(
        self,
        scenes: List[Scene],
        project_bible: Dict[str, Any],
        output_path: Path | str,
    ) -> Dict[str, Any]:
        payload = {
            "vml_version": "0.1",
            "project_id": project_bible.get("project_id", ""),
            "title": project_bible.get("title", ""),
            "scenes": [self.generate_scene_vml(scene, project_bible) for scene in scenes],
        }
        write_json_file(Path(output_path), payload)
        return payload

    def _emotion_for_scene(self, scene: Scene) -> str:
        if scene.dramatic_function == "hook_opening":
            return "focused curiosity"
        if scene.dramatic_function == "next_episode_hook":
            return "restrained shock or unresolved tension"
        if scene.dramatic_function == "conflict_or_action":
            return "controlled intensity"
        if scene.dramatic_function == "reveal_or_dialogue":
            return "calm but alert"
        return "story-forward concentration"

    def _camera_plan(self, scene: Scene) -> List[Dict[str, Any]]:
        third = round(scene.duration_sec / 3.0, 1)
        return [
            {"shot": "wide", "duration_sec": third, "description": "공간과 인물 위치를 확립한다."},
            {"shot": "medium", "duration_sec": third, "description": "인물 감정과 행동을 보여준다."},
            {"shot": "close_up", "duration_sec": max(1.0, scene.duration_sec - third * 2), "description": "핵심 후킹 이미지 또는 대사를 강조한다."},
        ]

    def _narration_stub(self, scene: Scene) -> str:
        return f"{scene.title}: {scene.dramatic_function} 장면. 작가 원고를 기반으로 최종 내레이션을 작성한다."

    def _keyframes(self, scene: Scene) -> List[Dict[str, Any]]:
        return [
            {"keyframe_id": "start", "time_sec": 0, "description": f"{scene.title} 시작 이미지"},
            {"keyframe_id": "mid", "time_sec": round(scene.duration_sec / 2.0, 1), "description": f"{scene.title} 중간 핵심 이미지"},
            {"keyframe_id": "end", "time_sec": scene.duration_sec, "description": f"{scene.title} 종료 후킹 이미지"},
        ]
