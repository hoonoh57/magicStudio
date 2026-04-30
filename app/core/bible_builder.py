from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from app.core.models import IdeaAnalysis, Project, write_json_file


class BibleBuilder:
    """Build a project bible from structured idea analysis.

    This MVP builder is rule-based and provider-free. It creates a stable
    production data object that later engines can consume.
    """

    def build(self, project: Project, analysis: IdeaAnalysis) -> Dict[str, Any]:
        genre = project.genre
        visual_style = self._visual_style_for_genre(genre)
        bible: Dict[str, Any] = {
            "project_id": project.project_id,
            "title": project.title,
            "genre": genre,
            "target_format": project.target_format,
            "core_hook": analysis.core_hook,
            "target_audience": analysis.target_audience,
            "format_candidates": analysis.format_candidates,
            "production_principles": [
                "작품은 작가에게 맡기고 제작 공정은 데이터화한다.",
                "프롬프트가 아니라 프롬프트를 만들 수 있는 구조를 저장한다.",
                "VML과 timeline.json을 내부 표준으로 사용한다.",
                "사용자 원고와 제작 자산은 로컬 전용으로 관리한다.",
            ],
            "visual_style": visual_style,
            "motifs": self._motifs_for_genre(genre, analysis.raw_text),
            "character_defaults": self._character_defaults(genre),
            "location_defaults": self._location_defaults(genre),
            "tts_profile": self._tts_profile(genre),
            "music_profile": self._music_profile(genre),
            "vml_rules": [
                "각 key scene은 목적, 감정, 카메라, 대사, 음향, 자막 정보를 가진다.",
                "동작은 motion_ref 또는 action_ref로 참조 가능해야 한다.",
                "실제 이미지/동영상/음성 파일은 로컬 asset_library 또는 local_projects 아래에서 참조한다.",
            ],
        }
        return bible

    def build_and_save(self, project: Project, analysis: IdeaAnalysis) -> Dict[str, Any]:
        bible = self.build(project, analysis)
        root_path = Path(project.root_path)
        write_json_file(root_path / "bible" / "project_bible.json", bible)
        return bible

    def _visual_style_for_genre(self, genre: str) -> Dict[str, Any]:
        if genre == "modern_wuxia":
            return {
                "style_name": "modern_urban_cinematic_wuxia",
                "description": "차가운 현대 도시감과 정통 무협의 검로·기운·절제된 대사를 결합한 시네마틱 스타일",
                "palette": ["cold blue", "concrete gray", "white energy line", "dark crimson"],
                "avoid": ["과도한 만화풍", "무작위 복장 변경", "장면마다 달라지는 얼굴"],
            }
        if genre == "horror":
            return {
                "style_name": "quiet_cinematic_horror",
                "description": "정적, 그림자, 낮은 대비, 소리 중심의 긴장감을 강조하는 스타일",
                "palette": ["desaturated gray", "deep shadow", "sickly green"],
                "avoid": ["정체를 너무 빨리 드러내기", "과도한 점프스케어"],
            }
        if genre == "education":
            return {
                "style_name": "clean_explainer",
                "description": "개념을 단계별로 보여주는 선명한 설명형 스타일",
                "palette": ["white", "blue", "dark text"],
                "avoid": ["한 장면에 여러 개념을 동시에 넣기"],
            }
        return {
            "style_name": "general_cinematic_story",
            "description": "장면 감정과 핵심 이미지를 우선하는 범용 시네마틱 스타일",
            "palette": ["neutral", "accent", "dark"],
            "avoid": ["캐릭터 일관성 붕괴", "장면 톤 급변"],
        }

    def _motifs_for_genre(self, genre: str, raw_text: str) -> list[str]:
        motifs: list[str] = []
        if genre == "modern_wuxia":
            motifs.extend(["밥", "검", "법", "등록", "도리", "기운"])
        if "기업" in raw_text:
            motifs.append("자본")
        if "국가" in raw_text or "법" in raw_text:
            motifs.append("제도")
        if not motifs:
            motifs.extend(["후킹", "인물", "장면", "다음 화 욕구"])
        return motifs

    def _character_defaults(self, genre: str) -> Dict[str, Any]:
        return {
            "main_character": {
                "role": "protagonist",
                "consistency_required": True,
                "sheet_status": "needs_author_input",
            },
            "supporting_character": {
                "role": "support",
                "consistency_required": True,
                "sheet_status": "optional",
            },
        }

    def _location_defaults(self, genre: str) -> Dict[str, Any]:
        return {
            "primary_location": {
                "consistency_required": True,
                "sheet_status": "needs_author_input",
            }
        }

    def _tts_profile(self, genre: str) -> Dict[str, Any]:
        return {
            "narration": {
                "tone": "clear, restrained, story-forward",
                "speed": 0.95,
            },
            "dialogue": {
                "tone": "character-specific, not exaggerated",
                "speed": 1.0,
            },
        }

    def _music_profile(self, genre: str) -> Dict[str, Any]:
        if genre == "modern_wuxia":
            return {
                "base": "low urban drone with restrained traditional strings",
                "action": "short metallic hits and controlled percussion",
                "emotion": "thin string or breath-like pad, minimal melody",
            }
        return {
            "base": "subtle cinematic bed",
            "action": "rhythmic pulse",
            "emotion": "minimal pad",
        }
