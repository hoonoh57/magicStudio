from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.project_manager import ProjectManager


def main() -> int:
    parser = argparse.ArgumentParser(description="Run magicStudio Phase 1 smoke test.")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root. Local project data is created under local_projects/ and ignored by git.",
    )
    parser.add_argument(
        "--title",
        default="불법강호",
        help="Project title for the smoke test.",
    )
    parser.add_argument(
        "--idea",
        default="현대 서울에 깨어난 백 년 전 무인이 국가등록무림과 충돌하는 3분 시리즈",
        help="Raw idea text.",
    )
    args = parser.parse_args()

    manager = ProjectManager(workspace_root=Path(args.workspace))
    project = manager.create_project_from_idea(
        title=args.title,
        raw_idea=args.idea,
        target_format="3min_episode",
    )

    print("=== magicStudio Phase 1 Smoke Test ===")
    print(f"project_id: {project.project_id}")
    print(f"title: {project.title}")
    print(f"genre: {project.genre}")
    print(f"market_score: {project.market_score}")
    print(f"production_score: {project.production_score}")
    print(f"status: {project.status.value}")
    print(f"root_path: {project.root_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
