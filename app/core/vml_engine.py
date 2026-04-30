from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from app.core.models import Scene, write_json_file


class VmlEngine:
    """Convert key scenes into VML production commands."""

    MOTIF_KEYWORDS: List[str] = [
        "밥",
        "법",
        "사람",
        "검",
        "기운",
        "봉인",
        "광고",
        "전광판",
        "등록",
        "관리",
        "마지막",
    ]

    def generate_scene_vml(self, scene: Scene, project_bible: Dict[str, Any]) -> Dict[str, Any]:
        motifs = project_bible.get("motifs", [])
        visual_style = project_bible.get("visual_style", {})
        narration_text = self._narration_from_source(scene)
        vml: Dict[str, Any] = {
            "vml_version": "0.1",
            "scene_id": scene.scene_id,
            "scene_no": scene.scene_no,
            "title": scene.title,
            "purpose": scene.dramatic_function,
            "duration_sec": scene.duration_sec,
            "style_ref": visual_style.get("style_name", "general_cinematic_story"),
            "motifs": motifs,
            "source_text": scene.source_text,
            "location": {
                "location_ref": "primary_location",
                "description": self._location_hint(scene),
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
            "motion": self._motion_refs(scene),
            "dialogue": [],
            "narration": {
                "text": narration_text,
                "tts_ref": "narration",
                "quality_score": self._narration_quality_score(scene, narration_text),
                "preserved_keywords": self._preserved_keywords(narration_text),
            },
            "audio": {
                "bgm": self._bgm_cue(scene),
                "sfx": self._sfx_cues(scene),
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
                "작가 원고의 핵심 문장이 보존되었는지 확인",
                "밥/법/검/봉인 등 모티프 문장이 누락되지 않았는지 확인",
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

    def _narration_from_source(self, scene: Scene) -> str:
        text = self._normalize_text(scene.source_text)
        if not text:
            return f"{scene.title}."

        sentences = self._split_sentences(text)
        if not sentences:
            return text

        if scene.dramatic_function == "hook_opening":
            return self._join_sentences(self._select_sentences(sentences, required_count=2))
        if scene.dramatic_function == "next_episode_hook":
            return self._join_sentences(self._select_sentences(sentences, required_count=3, prefer_all=True))
        return self._join_sentences(self._select_sentences(sentences, required_count=3))

    def _select_sentences(self, sentences: List[str], required_count: int, prefer_all: bool = False) -> List[str]:
        if prefer_all and len(sentences) <= required_count + 1:
            return sentences
        if len(sentences) <= required_count:
            return sentences

        selected_indexes: List[int] = [0]
        motif_indexes: List[int] = []
        for index, sentence in enumerate(sentences):
            if self._sentence_has_motif(sentence):
                motif_indexes.append(index)

        for index in motif_indexes:
            if index not in selected_indexes:
                selected_indexes.append(index)
            if len(selected_indexes) >= required_count:
                break

        if len(selected_indexes) < required_count:
            last_index = len(sentences) - 1
            if last_index not in selected_indexes:
                selected_indexes.append(last_index)

        cursor = 1
        while len(selected_indexes) < required_count and cursor < len(sentences):
            if cursor not in selected_indexes:
                selected_indexes.append(cursor)
            cursor += 1

        selected_indexes = sorted(selected_indexes[:required_count])
        return [sentences[index] for index in selected_indexes]

    def _sentence_has_motif(self, sentence: str) -> bool:
        return any(keyword in sentence for keyword in self.MOTIF_KEYWORDS)

    def _preserved_keywords(self, text: str) -> List[str]:
        return [keyword for keyword in self.MOTIF_KEYWORDS if keyword in text]

    def _narration_quality_score(self, scene: Scene, narration_text: str) -> float:
        score = 60.0
        source_keywords = [keyword for keyword in self.MOTIF_KEYWORDS if keyword in scene.source_text]
        preserved_keywords = [keyword for keyword in source_keywords if keyword in narration_text]
        if source_keywords:
            score += 30.0 * (len(preserved_keywords) / len(source_keywords))
        if narration_text and narration_text[-1] in ".?!。！？다요오까":
            score += 5.0
        if 25 <= len(narration_text) <= 160:
            score += 5.0
        if score > 100.0:
            return 100.0
        return round(score, 2)

    def _normalize_text(self, text: str) -> str:
        normalized = " ".join(text.split())
        normalized = re.sub(r"\s+([.,!?。！？])", r"\1", normalized)
        normalized = re.sub(r"([.,!?。！？])([^\s])", r"\1 \2", normalized)
        return normalized.strip()

    def _split_sentences(self, text: str) -> List[str]:
        normalized = self._normalize_text(text)
        if not normalized:
            return []

        sentences: List[str] = []
        start = 0
        for match in re.finditer(r"[.!?。！？]", normalized):
            end = match.end()
            sentence = normalized[start:end].strip()
            if sentence:
                sentences.append(sentence)
            start = end
            while start < len(normalized) and normalized[start].isspace():
                start += 1

        tail = normalized[start:].strip()
        if tail:
            sentences.append(tail)
        return sentences

    def _join_sentences(self, sentences: List[str]) -> str:
        text = " ".join(sentence.strip() for sentence in sentences if sentence.strip())
        return self._normalize_text(text)

    def _location_hint(self, scene: Scene) -> str:
        if "서울역" in scene.title or "전광판" in scene.title:
            return "서울역 광장 또는 대형 LED 전광판 앞. 차가운 도시 조명과 군중 흐름."
        if "03" in scene.title or "방" in scene.title:
            return "지하 봉인실. 유리 상자, 차가운 조명, 낮은 기계음."
        if "관리원" in scene.title or "조사" in scene.title:
            return "국가무예관리원 내부. 조사실 또는 수련실."
        return "project_bible.location_defaults.primary_location을 기준으로 구체화한다."

    def _motion_refs(self, scene: Scene) -> List[Dict[str, Any]]:
        if any(word in scene.source_text for word in ["검", "무인", "수련", "기운"]):
            return [
                {
                    "motion_ref": "local_action_library.auto_select",
                    "action_category": "martial_arts_or_controlled_gesture",
                    "note": "실제 동작 자산은 로컬 asset_library에서 선택한다.",
                }
            ]
        return []

    def _bgm_cue(self, scene: Scene) -> str:
        if scene.dramatic_function == "next_episode_hook":
            return "low tension drone with unresolved ending"
        if scene.dramatic_function == "conflict_or_action":
            return "controlled pulse with metallic accent"
        return "subtle cinematic bed"

    def _sfx_cues(self, scene: Scene) -> List[str]:
        cues: List[str] = []
        if "전광판" in scene.title:
            cues.extend(["city_ambience", "led_billboard_hum"])
        if "검" in scene.source_text:
            cues.append("faint_metal_resonance")
        if "방" in scene.title:
            cues.append("sealed_room_low_hum")
        return cues

    def _keyframes(self, scene: Scene) -> List[Dict[str, Any]]:
        sentences = self._split_sentences(scene.source_text)
        return [
            {"keyframe_id": "start", "time_sec": 0, "description": self._keyframe_sentence(scene.title, "시작 이미지", sentences, 0)},
            {"keyframe_id": "mid", "time_sec": round(scene.duration_sec / 2.0, 1), "description": self._keyframe_sentence(scene.title, "중간 핵심 이미지", sentences, self._middle_index(sentences))},
            {"keyframe_id": "end", "time_sec": scene.duration_sec, "description": self._keyframe_sentence(scene.title, "종료 후킹 이미지", sentences, len(sentences) - 1)},
        ]

    def _keyframe_sentence(self, title: str, label: str, sentences: List[str], index: int) -> str:
        if not sentences:
            return f"{title} {label}"
        safe_index = max(0, min(index, len(sentences) - 1))
        return f"{title} {label}: {sentences[safe_index]}"

    def _middle_index(self, sentences: List[str]) -> int:
        if not sentences:
            return 0
        return len(sentences) // 2
