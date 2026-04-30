from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from app.core.models import Episode, Scene, new_id, write_json_file


class SceneBreaker:
    """Break an episode scenario into key scenes.

    MVP rule:
    - Markdown headings become scene boundaries.
    - If no headings exist, paragraphs are grouped into 3~5 scene blocks.
    """

    def break_episode(self, episode: Episode, project_root: Path | str) -> List[Scene]:
        blocks = self._split_into_blocks(episode.scenario_text)
        scenes: List[Scene] = []
        for index, block in enumerate(blocks, start=1):
            title = block["title"] or f"Scene {index}"
            body = block["body"]
            scenes.append(
                Scene(
                    scene_id=new_id("scene"),
                    episode_id=episode.episode_id,
                    scene_no=index,
                    title=title,
                    dramatic_function=self._dramatic_function(body, index, len(blocks)),
                    duration_sec=self._estimate_duration(body),
                    status="DRAFT",
                )
            )

        root = Path(project_root)
        scene_payload: Dict[str, Any] = {
            "episode_id": episode.episode_id,
            "episode_title": episode.title,
            "scenes": [asdict(scene) for scene in scenes],
        }
        write_json_file(root / "episodes" / f"ep{episode.episode_no:03d}" / "scene_breakdown.json", scene_payload)
        return scenes

    def _split_into_blocks(self, scenario_text: str) -> List[Dict[str, str]]:
        lines = scenario_text.splitlines()
        heading_pattern = re.compile(r"^#{1,4}\s+(.+)$")
        blocks: List[Dict[str, str]] = []
        current_title = ""
        current_lines: List[str] = []

        for line in lines:
            match = heading_pattern.match(line.strip())
            if match:
                if current_lines:
                    blocks.append({"title": current_title, "body": "\n".join(current_lines).strip()})
                    current_lines = []
                current_title = match.group(1).strip()
            else:
                current_lines.append(line)

        if current_lines:
            blocks.append({"title": current_title, "body": "\n".join(current_lines).strip()})

        blocks = [block for block in blocks if block["body"]]
        if blocks:
            return blocks

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", scenario_text) if p.strip()]
        if not paragraphs:
            return [{"title": "Opening", "body": scenario_text.strip()}]

        group_size = max(1, len(paragraphs) // 4)
        grouped: List[Dict[str, str]] = []
        for start in range(0, len(paragraphs), group_size):
            grouped.append({"title": "", "body": "\n\n".join(paragraphs[start : start + group_size])})
        return grouped

    def _dramatic_function(self, body: str, scene_no: int, total: int) -> str:
        if scene_no == 1:
            return "hook_opening"
        if scene_no == total:
            return "next_episode_hook"
        if any(word in body for word in ["싸", "검", "추격", "폭발", "위기"]):
            return "conflict_or_action"
        if any(word in body for word in ["고백", "묻", "말", "대화", "설명"]):
            return "reveal_or_dialogue"
        return "story_progression"

    def _estimate_duration(self, body: str) -> float:
        chars = len(body.replace("\n", ""))
        seconds = max(12.0, min(75.0, chars / 18.0))
        return round(seconds, 1)
