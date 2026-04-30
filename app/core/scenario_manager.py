from __future__ import annotations

from pathlib import Path

from app.core.models import Episode, new_id, utc_now


class ScenarioManager:
    """Manage episode source scenarios stored in local project folders."""

    def register_episode(
        self,
        project_id: str,
        project_root: Path | str,
        episode_no: int,
        title: str,
        scenario_text: str,
    ) -> Episode:
        text = scenario_text.strip()
        if not text:
            raise ValueError("scenario_text is required")
        now = utc_now()
        episode = Episode(
            episode_id=new_id("episode"),
            project_id=project_id,
            episode_no=episode_no,
            title=title.strip() or f"Episode {episode_no}",
            scenario_text=text,
            created_at=now,
            updated_at=now,
        )
        root = Path(project_root)
        episode_dir = root / "episodes" / f"ep{episode_no:03d}"
        episode_dir.mkdir(parents=True, exist_ok=True)
        (episode_dir / "scenario.md").write_text(text, encoding="utf-8")
        return episode
