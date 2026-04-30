from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from app.core.asset_registry import AssetRegistry
from app.core.bible_builder import BibleBuilder
from app.core.idea_analyzer import IdeaAnalyzer
from app.core.production_planner import ProductionPlanner
from app.core.project_manager import ProjectManager
from app.core.scenario_manager import ScenarioManager
from app.core.scene_breaker import SceneBreaker
from app.core.timeline_builder import TimelineBuilder
from app.core.vml_engine import VmlEngine
from app.exporters.ffmpeg_preview_renderer import FfmpegPreviewRenderer
from app.exporters.srt_exporter import SrtExporter

ROOT_DIR = Path(__file__).resolve().parents[2]

DEFAULT_TITLE = "불법강호"
DEFAULT_IDEA = "현대 서울에 깨어난 백 년 전 무인이 국가등록무림과 충돌하는 3분 시리즈"
DEFAULT_SCENARIO = """# 서울역 전광판

백 년 전, 내가 죽인 놈의 문양이 서울역 전광판에서 광고가 되어 있었다.
이청은 사람들 사이에 멈춰 섰다.

# 국가무예관리원

서연화는 그를 조사실로 데려갔다.
하지만 이청은 법보다 먼저 밥을 물었다.

# 03번 방

권무혁은 지하 5층의 봉인실을 열었다.
유리 상자 안에는 부러진 검이 있었다.

# 다음 화 후킹

검의 단면에서 검은 기운이 아주 느리게 자라고 있었다.
권무혁이 말했다. 삼 년 뒤, 서울 한복판에서 저 봉인이 터질 수 있다.
"""


def read_text_smart(path: Path) -> str:
    if not path.exists():
        return ""
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def write_text_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(read_text_smart(path))
    except json.JSONDecodeError:
        return {}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_project_name(title: str) -> str:
    value = (title or DEFAULT_TITLE).strip() or DEFAULT_TITLE
    for ch in '<>:"/\\|?*':
        value = value.replace(ch, "_")
    return value


def project_root(workspace: Path, title: str) -> Path:
    return workspace / "local_projects" / safe_project_name(title)


def episode_dir(workspace: Path, title: str) -> Path:
    return project_root(workspace, title) / "episodes" / "ep001"


def save_project(workspace: Path, title: str, idea: str, scenario: str) -> Dict[str, Any]:
    root = project_root(workspace, title)
    ep_dir = episode_dir(workspace, title)
    root.mkdir(parents=True, exist_ok=True)
    ep_dir.mkdir(parents=True, exist_ok=True)
    write_json(root / "project.json", {"title": title, "idea": idea, "status": "draft"})
    write_json(ep_dir / "web_meta.json", {"title": title, "idea": idea, "scenario_path": str(ep_dir / "scenario.md")})
    write_text_utf8(ep_dir / "scenario.md", scenario)
    return {
        "title": title,
        "project_root": str(root),
        "episode_dir": str(ep_dir),
        "scenario_path": str(ep_dir / "scenario.md"),
    }


def load_project(workspace: Path, title: str) -> Dict[str, Any]:
    root = project_root(workspace, title)
    ep_dir = episode_dir(workspace, title)
    project = read_json(root / "project.json")
    meta = read_json(ep_dir / "web_meta.json")
    scenario = read_text_smart(ep_dir / "scenario.md") or DEFAULT_SCENARIO
    preview_path = ep_dir / "preview" / "preview.mp4"
    report_path = ep_dir / "asset_report.md"
    return {
        "ok": True,
        "title": title,
        "idea": meta.get("idea") or project.get("idea", DEFAULT_IDEA),
        "scenario": scenario,
        "project": project,
        "project_root": str(root),
        "episode_dir": str(ep_dir),
        "scenario_path": str(ep_dir / "scenario.md"),
        "exists": root.exists(),
        "keyframe_prompts": read_json(ep_dir / "keyframe_prompts.json") or None,
        "asset_manifest": read_json(ep_dir / "asset_manifest.json") or None,
        "preview_result": read_json(ep_dir / "preview" / "preview_render_result.json") or None,
        "preview_url": f"/media/{safe_project_name(title)}/episodes/ep001/preview/preview.mp4" if preview_path.exists() else "",
        "asset_report": read_text_smart(report_path) if report_path.exists() else "",
    }


def list_projects(workspace: Path) -> List[Dict[str, str]]:
    root = workspace / "local_projects"
    rows: List[Dict[str, str]] = []
    if not root.exists():
        return rows
    for item in sorted(root.iterdir(), key=lambda p: p.name):
        if not item.is_dir():
            continue
        project = read_json(item / "project.json")
        title = str(project.get("title", item.name))
        manifest = read_json(item / "episodes" / "ep001" / "asset_manifest.json")
        summary = manifest.get("summary", {}) if manifest else {}
        status = "draft"
        if summary:
            status = f"assets {summary.get('existing', 0)}/{summary.get('total', 0)} missing {summary.get('missing', 0)}"
        rows.append({"title": title, "path": str(item), "status": status})
    return rows


def build_pipeline(workspace: Path, title: str, idea: str, scenario: str) -> Dict[str, Any]:
    save_project(workspace, title, idea, scenario)
    manager = ProjectManager(workspace_root=workspace)
    project = manager.create_project_from_idea(title, idea, target_format="3min_episode")
    analysis = IdeaAnalyzer().analyze(idea)
    bible = BibleBuilder().build_and_save(project, analysis)
    episode = ScenarioManager().register_episode(
        project_id=project.project_id,
        project_root=project.root_path,
        episode_no=1,
        title="파일럿",
        scenario_text=scenario,
    )
    scenes = SceneBreaker().break_episode(episode, project.root_path)
    ep_dir = Path(project.root_path) / "episodes" / "ep001"
    vml_path = ep_dir / "vml_scenes.json"
    vml_episode = VmlEngine().generate_episode_vml(scenes, bible, vml_path)
    timeline = TimelineBuilder().build_and_save(vml_episode, ep_dir / "timeline.json")
    SrtExporter().export_file(timeline, ep_dir / "captions.srt")
    production_files = ProductionPlanner().save_all(vml_episode, timeline, ep_dir)
    preview_plan = read_json(ep_dir / "preview_render_plan.json")
    tts_script = read_json(ep_dir / "tts_script.json")
    manifest = AssetRegistry().build_and_save(ep_dir, vml_episode, preview_plan, tts_script, None)
    return {
        "project_id": project.project_id,
        "project_root": str(project.root_path),
        "episode_dir": str(ep_dir),
        "scene_count": len(scenes),
        "production_files": {key: str(value) for key, value in production_files.items()},
        "asset_manifest": manifest,
    }


def synth_tts(workspace: Path, title: str, voice: str) -> Dict[str, Any]:
    ep_dir = episode_dir(workspace, title)
    command = [sys.executable, str(ROOT_DIR / "tools" / "synth_tts_windows.py"), str(ep_dir), "--voice", voice]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(workspace))
    result_path = ep_dir / "audio" / "tts_synthesis_result.json"
    payload = read_json(result_path)
    payload["returncode"] = completed.returncode
    payload["stdout"] = completed.stdout
    payload["stderr"] = completed.stderr
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout or "TTS failed")
    return payload


def render_preview_video(workspace: Path, title: str, burn_subtitles: bool) -> Dict[str, Any]:
    ep_dir = episode_dir(workspace, title)
    renderer = FfmpegPreviewRenderer(burn_subtitles=burn_subtitles)
    result = renderer.render_from_file(ep_dir)
    vml = read_json(ep_dir / "vml_scenes.json")
    preview_plan = read_json(ep_dir / "preview_render_plan.json")
    tts_script = read_json(ep_dir / "tts_script.json")
    AssetRegistry().build_and_save(ep_dir, vml, preview_plan, tts_script, result)
    return result


def inspect_assets(workspace: Path, title: str) -> Dict[str, Any]:
    command = [sys.executable, str(ROOT_DIR / "tools" / "inspect_assets.py"), str(episode_dir(workspace, title))]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(workspace))
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout or "inspect failed")
    ep_dir = episode_dir(workspace, title)
    manifest = read_json(ep_dir / "asset_manifest.json")
    report = read_text_smart(ep_dir / "asset_report.md")
    return {"manifest": manifest, "report": report, "missing": manifest.get("summary", {}).get("missing", 0)}


def make_all(workspace: Path, title: str, idea: str, scenario: str, voice: str, burn_subtitles: bool) -> Dict[str, Any]:
    pipeline = build_pipeline(workspace, title, idea, scenario)
    tts = synth_tts(workspace, title, voice)
    preview = render_preview_video(workspace, title, burn_subtitles)
    inspection = inspect_assets(workspace, title)
    return {"pipeline": pipeline, "tts": tts, "preview": preview, "inspection": inspection}
