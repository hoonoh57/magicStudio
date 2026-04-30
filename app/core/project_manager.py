from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.core.db import Database
from app.core.idea_analyzer import IdeaAnalyzer
from app.core.market_evaluator import MarketEvaluator
from app.core.models import Decision, Project, ProjectStatus, new_id, safe_slug, utc_now, write_json_file
from app.core.production_evaluator import ProductionEvaluator


class ProjectManager:
    """Create and persist magicStudio projects.

    The manager owns only project metadata and folder structure. It does not
    generate images, TTS, or timelines directly.
    """

    def __init__(self, workspace_root: Path | str, db_path: Optional[Path | str] = None) -> None:
        self.workspace_root = Path(workspace_root)
        self.projects_root = self.workspace_root / "local_projects"
        self.projects_root.mkdir(parents=True, exist_ok=True)
        self.db = Database(db_path or (self.workspace_root / "magicstudio.local.sqlite3"))
        self.db.initialize()
        self.idea_analyzer = IdeaAnalyzer()
        self.market_evaluator = MarketEvaluator()
        self.production_evaluator = ProductionEvaluator()

    def create_project_from_idea(
        self,
        title: str,
        raw_idea: str,
        target_format: str = "3min_episode",
    ) -> Project:
        analysis = self.idea_analyzer.analyze(raw_idea)
        market = self.market_evaluator.evaluate(analysis)
        production = self.production_evaluator.evaluate(analysis)

        genre = analysis.detected_genres[0] if analysis.detected_genres else "general_story"
        project_id = new_id("project")
        slug = safe_slug(title, fallback=project_id)
        root_path = self.projects_root / slug
        self._create_project_folders(root_path)

        status = ProjectStatus.READY
        if market.decision in (Decision.HOLD, Decision.REJECT) or production.decision in (Decision.HOLD, Decision.REJECT):
            status = ProjectStatus.DRAFT

        now = utc_now()
        project = Project(
            project_id=project_id,
            title=title,
            genre=genre,
            target_format=target_format,
            root_path=str(root_path),
            market_score=market.score,
            production_score=production.score,
            status=status,
            created_at=now,
            updated_at=now,
        )

        self._persist_project(project)
        self._persist_idea(project.project_id, analysis, market.score, production.score, market.decision.value)
        self._write_project_files(project, analysis.to_json(), market.to_json(), production.to_json())
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        row = self.db.fetch_one(
            "SELECT * FROM projects WHERE project_id = ?",
            (project_id,),
        )
        if row is None:
            return None
        return Project(
            project_id=str(row["project_id"]),
            title=str(row["title"]),
            genre=str(row["genre"]),
            target_format=str(row["target_format"]),
            root_path=str(row["root_path"]),
            market_score=float(row["market_score"]),
            production_score=float(row["production_score"]),
            status=ProjectStatus(str(row["status"])),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _create_project_folders(self, root_path: Path) -> None:
        folders = [
            root_path,
            root_path / "bible",
            root_path / "episodes",
            root_path / "source",
            root_path / "assets",
            root_path / "assets" / "raw",
            root_path / "assets" / "user",
            root_path / "assets" / "motions",
            root_path / "assets" / "sprites",
            root_path / "assets" / "poses",
            root_path / "assets" / "references",
            root_path / "exports",
            root_path / "renders",
        ]
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)

    def _persist_project(self, project: Project) -> None:
        data = project.to_dict()
        self.db.execute(
            """
            INSERT INTO projects (
                project_id, title, genre, target_format, root_path,
                market_score, production_score, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["project_id"],
                data["title"],
                data["genre"],
                data["target_format"],
                data["root_path"],
                data["market_score"],
                data["production_score"],
                data["status"],
                data["created_at"],
                data["updated_at"],
            ),
        )

    def _persist_idea(
        self,
        project_id: str,
        analysis: object,
        market_score: float,
        production_score: float,
        decision: str,
    ) -> None:
        # analysis is IdeaAnalysis; keep explicit attribute access to avoid coupling
        self.db.execute(
            """
            INSERT INTO ideas (
                idea_id, project_id, raw_text, detected_genre, core_hook,
                target_audience, format_candidates, risk_flags,
                market_score, production_score, decision, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis.idea_id,
                project_id,
                analysis.raw_text,
                json.dumps(analysis.detected_genres, ensure_ascii=False),
                analysis.core_hook,
                json.dumps(analysis.target_audience, ensure_ascii=False),
                json.dumps(analysis.format_candidates, ensure_ascii=False),
                json.dumps(analysis.risk_flags, ensure_ascii=False),
                market_score,
                production_score,
                decision,
                analysis.created_at,
            ),
        )

    def _write_project_files(
        self,
        project: Project,
        analysis_json: str,
        market_json: str,
        production_json: str,
    ) -> None:
        root_path = Path(project.root_path)
        write_json_file(root_path / "project.json", project.to_dict())
        (root_path / "idea_analysis.json").write_text(analysis_json, encoding="utf-8")
        (root_path / "market_evaluation.json").write_text(market_json, encoding="utf-8")
        (root_path / "production_evaluation.json").write_text(production_json, encoding="utf-8")
