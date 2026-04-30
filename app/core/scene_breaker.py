from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from app.core.models import Episode, Scene, new_id, write_json_file


class SceneBreaker:
    """Break an episode scenario into production-sized scenes.

    Production rule:
    - Markdown headings remain major scene boundaries.
    - A long heading block is automatically split into smaller production scenes.
    - If no headings exist, paragraphs/sentences are grouped into production scenes.

    The goal is not to split episodes into arbitrary 3-scene summaries. One episode
    may become 8, 15, or 30 scenes depending on source length. Each generated scene
    keeps its full source_text so TTS, subtitles, keyframes, and preview segments can
    be generated for the whole episode rather than only the first few sentences.
    """

    TARGET_SCENE_CHARS = 520
    HARD_MAX_SCENE_CHARS = 760
    MIN_SCENE_CHARS = 180

    def break_episode(self, episode: Episode, project_root: Path | str) -> List[Scene]:
        blocks = self._split_into_blocks(episode.scenario_text)
        scenes: List[Scene] = []
        for block in blocks:
            title = block["title"] or "Scene"
            body = block["body"]
            sub_blocks = self._split_long_body(body)
            for part_no, sub_body in enumerate(sub_blocks, start=1):
                scene_no = len(scenes) + 1
                scene_title = self._scene_title(title, part_no, len(sub_blocks), scene_no)
                scenes.append(
                    Scene(
                        scene_id=new_id("scene"),
                        episode_id=episode.episode_id,
                        scene_no=scene_no,
                        title=scene_title,
                        dramatic_function=self._dramatic_function(sub_body, scene_no, 0),
                        duration_sec=self._estimate_duration(sub_body),
                        source_text=sub_body,
                        status="DRAFT",
                    )
                )

        total = len(scenes)
        for scene in scenes:
            scene.dramatic_function = self._dramatic_function(scene.source_text, scene.scene_no, total)

        root = Path(project_root)
        scene_payload: Dict[str, Any] = {
            "episode_id": episode.episode_id,
            "episode_title": episode.title,
            "split_policy": {
                "target_scene_chars": self.TARGET_SCENE_CHARS,
                "hard_max_scene_chars": self.HARD_MAX_SCENE_CHARS,
                "min_scene_chars": self.MIN_SCENE_CHARS,
                "scene_count": len(scenes),
                "note": "Long episode text is split into production scenes before TTS/keyframe/video generation.",
            },
            "scenes": [asdict(scene) for scene in scenes],
        }
        write_json_file(root / "episodes" / f"ep{episode.episode_no:03d}" / "scene_breakdown.json", scene_payload)
        return scenes

    def _split_into_blocks(self, scenario_text: str) -> List[Dict[str, str]]:
        lines = scenario_text.splitlines()
        heading_pattern = re.compile(r"^#{1,4}\s+(.+)$")
        numbered_heading_pattern = re.compile(r"^\s*(?:제\s*)?\d+\s*(?:화|장|막|절|\.\s+)\s*(.*)$")
        blocks: List[Dict[str, str]] = []
        current_title = ""
        current_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            match = heading_pattern.match(stripped)
            numbered_match = numbered_heading_pattern.match(stripped)
            if match or numbered_match:
                title = match.group(1).strip() if match else stripped
                if current_lines:
                    blocks.append({"title": current_title, "body": "\n".join(current_lines).strip()})
                    current_lines = []
                current_title = title
            else:
                current_lines.append(line)

        if current_lines:
            blocks.append({"title": current_title, "body": "\n".join(current_lines).strip()})

        blocks = [block for block in blocks if block["body"]]
        if blocks:
            return blocks

        normalized = scenario_text.strip()
        if not normalized:
            return [{"title": "Opening", "body": ""}]
        return [{"title": "Opening", "body": normalized}]

    def _split_long_body(self, body: str) -> List[str]:
        units = self._text_units(body)
        if not units:
            cleaned = body.strip()
            return [cleaned] if cleaned else []

        scenes: List[str] = []
        current: List[str] = []
        current_len = 0

        for unit in units:
            unit_len = len(unit)
            if current and self._should_flush(current_len, unit_len):
                scenes.append(self._join_units(current))
                current = [unit]
                current_len = unit_len
            else:
                current.append(unit)
                current_len += unit_len

            if current_len >= self.HARD_MAX_SCENE_CHARS:
                scenes.append(self._join_units(current))
                current = []
                current_len = 0

        if current:
            scenes.append(self._join_units(current))

        return self._rebalance_short_scenes(scenes)

    def _text_units(self, body: str) -> List[str]:
        normalized = body.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized:
            return []

        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", normalized) if paragraph.strip()]
        units: List[str] = []
        for paragraph in paragraphs:
            if len(paragraph) <= self.HARD_MAX_SCENE_CHARS:
                units.append(paragraph)
            else:
                units.extend(self._split_paragraph_to_sentences(paragraph))
        return [unit for unit in units if unit.strip()]

    def _split_paragraph_to_sentences(self, paragraph: str) -> List[str]:
        normalized = " ".join(paragraph.split())
        sentences: List[str] = []
        start = 0
        for match in re.finditer(r"[.!?。！？]|[다요까죠네음임함]([.\s]|$)", normalized):
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
        if not sentences:
            return self._split_by_length(normalized)

        expanded: List[str] = []
        for sentence in sentences:
            if len(sentence) > self.HARD_MAX_SCENE_CHARS:
                expanded.extend(self._split_by_length(sentence))
            else:
                expanded.append(sentence)
        return expanded

    def _split_by_length(self, text: str) -> List[str]:
        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + self.TARGET_SCENE_CHARS)
            if end < len(text):
                boundary = max(text.rfind(" ", start, end), text.rfind(".", start, end), text.rfind("다", start, end))
                if boundary > start + self.MIN_SCENE_CHARS:
                    end = boundary + 1
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end
        return chunks

    def _should_flush(self, current_len: int, next_len: int) -> bool:
        if current_len >= self.TARGET_SCENE_CHARS and current_len + next_len > self.TARGET_SCENE_CHARS + 80:
            return True
        if current_len >= self.MIN_SCENE_CHARS and current_len + next_len > self.HARD_MAX_SCENE_CHARS:
            return True
        return False

    def _rebalance_short_scenes(self, scenes: List[str]) -> List[str]:
        if len(scenes) <= 1:
            return scenes
        balanced: List[str] = []
        for scene in scenes:
            if balanced and len(scene) < self.MIN_SCENE_CHARS and len(balanced[-1]) + len(scene) <= self.HARD_MAX_SCENE_CHARS:
                balanced[-1] = self._join_units([balanced[-1], scene])
            else:
                balanced.append(scene)
        return balanced

    def _join_units(self, units: List[str]) -> str:
        return "\n\n".join(unit.strip() for unit in units if unit.strip()).strip()

    def _scene_title(self, title: str, part_no: int, total_parts: int, scene_no: int) -> str:
        base = title.strip() or f"Scene {scene_no:02d}"
        if total_parts <= 1:
            return base
        return f"{base}-{part_no:02d}"

    def _dramatic_function(self, body: str, scene_no: int, total: int) -> str:
        if scene_no == 1:
            return "hook_opening"
        if total > 0 and scene_no == total:
            return "next_episode_hook"
        if any(word in body for word in ["싸", "검", "추격", "폭발", "위기", "죽", "피", "부러", "공격"]):
            return "conflict_or_action"
        if any(word in body for word in ["고백", "묻", "말", "대화", "설명", "속삭", "대답"]):
            return "reveal_or_dialogue"
        return "story_progression"

    def _estimate_duration(self, body: str) -> float:
        chars = len(body.replace("\n", ""))
        seconds = max(8.0, min(75.0, chars / 7.0))
        return round(seconds, 1)
