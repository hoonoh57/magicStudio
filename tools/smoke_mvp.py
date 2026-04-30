from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.bible_builder import BibleBuilder
from app.core.idea_analyzer import IdeaAnalyzer
from app.core.project_manager import ProjectManager
from app.core.scenario_manager import ScenarioManager
from app.core.scene_breaker import SceneBreaker
from app.core.timeline_builder import TimelineBuilder
from app.core.vml_engine import VmlEngine
from app.exporters.srt_exporter import SrtExporter


DEFAULT_IDEA = "현대 서울에 깨어난 백 년 전 무인이 국가등록무림과 충돌하는 3분 시리즈"

DEFAULT_SCENARIO = """# 서울역 전광판

백 년 전, 내가 죽인 놈의 문양이 서울역 전광판에서 광고가 되어 있었다.
이청은 사람들 사이에 멈춰 섰다. 몸은 굶주렸고 단전은 비어 있었지만, 눈만은 아직 백 년 전의 검을 기억하고 있었다.

# 국가무예관리원

서연화는 그를 조사실로 데려갔다. 미등록 기사용 감지망에 잡힌 자는 법에 따라 관리되어야 했다.
하지만 이청은 법보다 먼저 밥을 물었다. 검존이기 전에 사람이기 때문이었다.

# 03번 방

권무혁은 지하 5층의 봉인실을 열었다. 유리 상자 안에는 부러진 검이 있었다.
이청은 그 검을 보고 한동안 말하지 못했다. 그 검은 백 년 전 그의 손에서 부러진 매화잔설이었다.

# 다음 화 후킹

검의 단면에서 검은 기운이 아주 느리게 자라고 있었다.
권무혁이 말했다. 삼 년 뒤, 서울 한복판에서 저 봉인이 터질 수 있다.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full magicStudio MVP smoke pipeline.")
    parser.add_argument("--workspace", default=".", help="Workspace root")
    parser.add_argument("--title", default="불법강호", help="Project title")
    parser.add_argument("--idea", default=DEFAULT_IDEA, help="Idea text")
    parser.add_argument("--scenario-file", default="", help="Optional UTF-8 scenario markdown file")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    manager = ProjectManager(workspace_root=workspace)
    project = manager.create_project_from_idea(args.title, args.idea, target_format="3min_episode")

    analysis = IdeaAnalyzer().analyze(args.idea)
    bible = BibleBuilder().build_and_save(project, analysis)

    scenario_text = DEFAULT_SCENARIO
    if args.scenario_file:
        scenario_text = Path(args.scenario_file).read_text(encoding="utf-8")

    episode = ScenarioManager().register_episode(
        project_id=project.project_id,
        project_root=project.root_path,
        episode_no=1,
        title="파일럿",
        scenario_text=scenario_text,
    )

    scenes = SceneBreaker().break_episode(episode, project.root_path)
    episode_dir = Path(project.root_path) / "episodes" / "ep001"
    vml_path = episode_dir / "vml_scenes.json"
    vml_episode = VmlEngine().generate_episode_vml(scenes, bible, vml_path)

    timeline_path = episode_dir / "timeline.json"
    timeline = TimelineBuilder().build_and_save(vml_episode, timeline_path)

    srt_path = episode_dir / "captions.srt"
    SrtExporter().export_file(timeline, srt_path)

    print("=== magicStudio MVP Smoke Pipeline ===")
    print(f"project_id: {project.project_id}")
    print(f"project_root: {project.root_path}")
    print(f"project_bible: {Path(project.root_path) / 'bible' / 'project_bible.json'}")
    print(f"scene_breakdown: {episode_dir / 'scene_breakdown.json'}")
    print(f"vml_scenes: {vml_path}")
    print(f"timeline: {timeline_path}")
    print(f"captions: {srt_path}")
    print(f"scene_count: {len(scenes)}")
    print(f"duration_sec: {timeline.get('duration_sec')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
