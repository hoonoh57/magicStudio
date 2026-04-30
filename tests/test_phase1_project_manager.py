from pathlib import Path

from app.core.idea_analyzer import IdeaAnalyzer
from app.core.market_evaluator import MarketEvaluator
from app.core.models import ProjectStatus
from app.core.production_evaluator import ProductionEvaluator
from app.core.project_manager import ProjectManager


def test_idea_analyzer_detects_modern_wuxia() -> None:
    analyzer = IdeaAnalyzer()
    analysis = analyzer.analyze("현대 서울에 깨어난 백 년 전 무인이 국가등록무림과 충돌하는 이야기")

    assert "modern_wuxia" in analysis.detected_genres
    assert "webnovel_fans" in analysis.target_audience
    assert analysis.core_hook


def test_market_and_production_evaluators_return_scores() -> None:
    analysis = IdeaAnalyzer().analyze(
        "현대 서울역에서 백 년 전 무인이 깨어나 국가등록무림의 법과 충돌하는 3분 시리즈"
    )

    market = MarketEvaluator().evaluate(analysis)
    production = ProductionEvaluator().evaluate(analysis)

    assert market.score > 0
    assert production.score > 0
    assert market.decision.value in {"MAKE_NOW", "MAKE_PILOT", "REVISE", "HOLD", "REJECT"}
    assert production.decision.value in {"MAKE_NOW", "MAKE_PILOT", "REVISE", "HOLD", "REJECT"}


def test_project_manager_creates_local_project_files(tmp_path: Path) -> None:
    manager = ProjectManager(workspace_root=tmp_path)
    project = manager.create_project_from_idea(
        title="불법강호",
        raw_idea="현대 서울에 깨어난 백 년 전 무인이 국가등록무림과 충돌하는 3분 시리즈",
        target_format="3min_episode",
    )

    project_root = Path(project.root_path)
    assert project.project_id.startswith("project_")
    assert project.status in {ProjectStatus.READY, ProjectStatus.DRAFT}
    assert (project_root / "project.json").exists()
    assert (project_root / "idea_analysis.json").exists()
    assert (project_root / "market_evaluation.json").exists()
    assert (project_root / "production_evaluation.json").exists()
    assert (project_root / "assets" / "motions").exists()
    assert manager.get_project(project.project_id) is not None
