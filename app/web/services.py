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


def safe_episode_id(episode_id: str) -> str:
    value = (episode_id or "ep001").strip().lower()
    if not value.startswith("ep"):
        value = "ep" + value
    digits = "".join(ch for ch in value if ch.isdigit())
    if digits:
        return "ep" + digits.zfill(3)
    return "ep001"


def project_root(workspace: Path, title: str) -> Path:
    return workspace / "local_projects" / safe_project_name(title)


def manuscript_dir(workspace: Path, title: str) -> Path:
    return project_root(workspace, title) / "manuscript"


def chunks_dir(workspace: Path, title: str) -> Path:
    return manuscript_dir(workspace, title) / "chunks"


def episode_dir(workspace: Path, title: str, episode_id: str = "ep001") -> Path:
    return project_root(workspace, title) / "episodes" / safe_episode_id(episode_id)


def save_project(workspace: Path, title: str, idea: str, scenario: str) -> Dict[str, Any]:
    root = project_root(workspace, title)
    ep_dir = episode_dir(workspace, title, "ep001")
    root.mkdir(parents=True, exist_ok=True)
    ep_dir.mkdir(parents=True, exist_ok=True)
    write_json(root / "project.json", {"title": title, "idea": idea, "status": "draft"})
    write_json(ep_dir / "web_meta.json", {"title": title, "idea": idea, "episode_id": "ep001", "scenario_path": str(ep_dir / "scenario.md")})
    write_text_utf8(ep_dir / "scenario.md", scenario)
    return {
        "title": title,
        "project_root": str(root),
        "episode_dir": str(ep_dir),
        "scenario_path": str(ep_dir / "scenario.md"),
    }


def save_manuscript(workspace: Path, title: str, idea: str, manuscript: str) -> Dict[str, Any]:
    root = project_root(workspace, title)
    m_dir = manuscript_dir(workspace, title)
    root.mkdir(parents=True, exist_ok=True)
    m_dir.mkdir(parents=True, exist_ok=True)
    project = read_json(root / "project.json")
    project["title"] = title
    project["idea"] = idea
    project["status"] = project.get("status", "draft")
    write_json(root / "project.json", project)
    write_text_utf8(m_dir / "full_manuscript.md", manuscript)
    meta = {
        "title": title,
        "idea": idea,
        "manuscript_path": str(m_dir / "full_manuscript.md"),
        "char_count": len(manuscript),
        "line_count": len(manuscript.splitlines()),
    }
    write_json(m_dir / "full_manuscript_meta.json", meta)
    return {"project_root": str(root), "manuscript_path": str(m_dir / "full_manuscript.md"), "meta": meta}


def load_manuscript(workspace: Path, title: str) -> Dict[str, Any]:
    m_dir = manuscript_dir(workspace, title)
    text = read_text_smart(m_dir / "full_manuscript.md")
    meta = read_json(m_dir / "full_manuscript_meta.json")
    return {"text": text, "meta": meta, "exists": bool(text)}


def split_text_to_chunks(text: str, target_chars: int = 2500) -> List[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    sections = []
    current: List[str] = []
    for line in normalized.split("\n"):
        if line.startswith("# ") and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    if len(sections) <= 1:
        paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
        sections = paragraphs if paragraphs else [normalized]

    chunks: List[str] = []
    buffer: List[str] = []
    size = 0
    for section in sections:
        section_len = len(section)
        if buffer and size + section_len > target_chars:
            chunks.append("\n\n".join(buffer).strip())
            buffer = [section]
            size = section_len
        else:
            buffer.append(section)
            size += section_len
    if buffer:
        chunks.append("\n\n".join(buffer).strip())
    return chunks


def split_manuscript(workspace: Path, title: str, target_chars: int = 2500) -> Dict[str, Any]:
    manuscript = load_manuscript(workspace, title)["text"]
    if not manuscript:
        raise RuntimeError("전체 원고가 없습니다. 먼저 전체 원고를 저장하세요.")
    c_dir = chunks_dir(workspace, title)
    c_dir.mkdir(parents=True, exist_ok=True)
    for old_file in c_dir.glob("chunk_*.md"):
        old_file.unlink()
    chunks = split_text_to_chunks(manuscript, target_chars)
    items: List[Dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        chunk_id = f"chunk_{index:04d}"
        path = c_dir / f"{chunk_id}.md"
        write_text_utf8(path, chunk)
        items.append({
            "chunk_id": chunk_id,
            "path": str(path),
            "char_count": len(chunk),
            "line_count": len(chunk.splitlines()),
            "preview": chunk[:180].replace("\n", " "),
        })
    index_payload = {"title": title, "target_chars": target_chars, "count": len(items), "chunks": items}
    write_json(c_dir / "chunks_index.json", index_payload)
    return index_payload


def list_chunks(workspace: Path, title: str) -> Dict[str, Any]:
    c_dir = chunks_dir(workspace, title)
    index_path = c_dir / "chunks_index.json"
    if index_path.exists():
        return read_json(index_path)
    items: List[Dict[str, Any]] = []
    for path in sorted(c_dir.glob("chunk_*.md")):
        text = read_text_smart(path)
        items.append({"chunk_id": path.stem, "path": str(path), "char_count": len(text), "line_count": len(text.splitlines()), "preview": text[:180].replace("\n", " ")})
    return {"title": title, "count": len(items), "chunks": items}


def load_chunk(workspace: Path, title: str, chunk_id: str) -> Dict[str, Any]:
    path = chunks_dir(workspace, title) / f"{chunk_id}.md"
    text = read_text_smart(path)
    return {"chunk_id": chunk_id, "path": str(path), "text": text, "exists": bool(text)}


def episode_summary(workspace: Path, title: str, episode_id: str) -> Dict[str, Any]:
    ep_id = safe_episode_id(episode_id)
    ep_dir = episode_dir(workspace, title, ep_id)
    scenario = read_text_smart(ep_dir / "scenario.md")
    meta = read_json(ep_dir / "web_meta.json")
    return {"episode_id": ep_id, "title": meta.get("episode_title", ep_id), "path": str(ep_dir), "char_count": len(scenario), "line_count": len(scenario.splitlines()), "preview": scenario[:160].replace("\n", " ")}


def list_episodes(workspace: Path, title: str) -> Dict[str, Any]:
    ep_root = project_root(workspace, title) / "episodes"
    items: List[Dict[str, Any]] = []
    if ep_root.exists():
        for item in sorted(ep_root.iterdir(), key=lambda p: p.name):
            if item.is_dir() and item.name.startswith("ep"):
                items.append(episode_summary(workspace, title, item.name))
    return {"title": title, "count": len(items), "episodes": items}


def save_episode(workspace: Path, title: str, episode_id: str, scenario: str, episode_title: str = "") -> Dict[str, Any]:
    ep_id = safe_episode_id(episode_id)
    ep_dir = episode_dir(workspace, title, ep_id)
    ep_dir.mkdir(parents=True, exist_ok=True)
    write_text_utf8(ep_dir / "scenario.md", scenario)
    meta = {"title": title, "episode_id": ep_id, "episode_title": episode_title or ep_id, "scenario_path": str(ep_dir / "scenario.md")}
    write_json(ep_dir / "web_meta.json", meta)
    return {"episode_id": ep_id, "episode_dir": str(ep_dir), "scenario_path": str(ep_dir / "scenario.md"), "char_count": len(scenario)}


def load_episode(workspace: Path, title: str, episode_id: str) -> Dict[str, Any]:
    ep_id = safe_episode_id(episode_id)
    ep_dir = episode_dir(workspace, title, ep_id)
    scenario = read_text_smart(ep_dir / "scenario.md") or DEFAULT_SCENARIO
    meta = read_json(ep_dir / "web_meta.json")
    return {"episode_id": ep_id, "episode_title": meta.get("episode_title", ep_id), "episode_dir": str(ep_dir), "scenario_path": str(ep_dir / "scenario.md"), "scenario": scenario, "exists": ep_dir.exists()}


def create_episode_from_chunk(workspace: Path, title: str, chunk_id: str, episode_id: str) -> Dict[str, Any]:
    chunk = load_chunk(workspace, title, chunk_id)
    if not chunk.get("text"):
        raise RuntimeError(f"선택한 chunk를 찾을 수 없습니다: {chunk_id}")
    saved = save_episode(workspace, title, episode_id, chunk["text"], episode_title=episode_id)
    saved["source_chunk_id"] = chunk_id
    return saved


def load_project(workspace: Path, title: str, episode_id: str = "ep001") -> Dict[str, Any]:
    root = project_root(workspace, title)
    ep_id = safe_episode_id(episode_id)
    ep_dir = episode_dir(workspace, title, ep_id)
    project = read_json(root / "project.json")
    meta = read_json(ep_dir / "web_meta.json")
    scenario = read_text_smart(ep_dir / "scenario.md") or DEFAULT_SCENARIO
    preview_path = ep_dir / "preview" / "preview.mp4"
    report_path = ep_dir / "asset_report.md"
    manuscript = load_manuscript(workspace, title)
    return {
        "ok": True,
        "title": title,
        "idea": meta.get("idea") or project.get("idea", DEFAULT_IDEA),
        "scenario": scenario,
        "project": project,
        "project_root": str(root),
        "episode_id": ep_id,
        "episode_dir": str(ep_dir),
        "scenario_path": str(ep_dir / "scenario.md"),
        "exists": root.exists(),
        "manuscript": manuscript,
        "chunks": list_chunks(workspace, title),
        "episodes": list_episodes(workspace, title),
        "keyframe_prompts": read_json(ep_dir / "keyframe_prompts.json") or None,
        "asset_manifest": read_json(ep_dir / "asset_manifest.json") or None,
        "preview_result": read_json(ep_dir / "preview" / "preview_render_result.json") or None,
        "preview_url": f"/media/{safe_project_name(title)}/episodes/{ep_id}/preview/preview.mp4" if preview_path.exists() else "",
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


def build_pipeline(workspace: Path, title: str, idea: str, scenario: str, episode_id: str = "ep001") -> Dict[str, Any]:
    ep_id = safe_episode_id(episode_id)
    save_episode(workspace, title, ep_id, scenario, episode_title=ep_id)
    manager = ProjectManager(workspace_root=workspace)
    project = manager.create_project_from_idea(title, idea, target_format="3min_episode")
    analysis = IdeaAnalyzer().analyze(idea)
    bible = BibleBuilder().build_and_save(project, analysis)
    episode_no = int("".join(ch for ch in ep_id if ch.isdigit()) or "1")
    episode = ScenarioManager().register_episode(
        project_id=project.project_id,
        project_root=project.root_path,
        episode_no=episode_no,
        title=ep_id,
        scenario_text=scenario,
    )
    scenes = SceneBreaker().break_episode(episode, project.root_path)
    ep_dir = Path(project.root_path) / "episodes" / ep_id
    ep_dir.mkdir(parents=True, exist_ok=True)
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
        "episode_id": ep_id,
        "episode_dir": str(ep_dir),
        "scene_count": len(scenes),
        "production_files": {key: str(value) for key, value in production_files.items()},
        "asset_manifest": manifest,
    }


def synth_tts(workspace: Path, title: str, voice: str, episode_id: str = "ep001") -> Dict[str, Any]:
    ep_dir = episode_dir(workspace, title, episode_id)
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


def render_preview_video(workspace: Path, title: str, burn_subtitles: bool, episode_id: str = "ep001") -> Dict[str, Any]:
    ep_dir = episode_dir(workspace, title, episode_id)
    renderer = FfmpegPreviewRenderer(burn_subtitles=burn_subtitles)
    result = renderer.render_from_file(ep_dir)
    vml = read_json(ep_dir / "vml_scenes.json")
    preview_plan = read_json(ep_dir / "preview_render_plan.json")
    tts_script = read_json(ep_dir / "tts_script.json")
    AssetRegistry().build_and_save(ep_dir, vml, preview_plan, tts_script, result)
    return result


def inspect_assets(workspace: Path, title: str, episode_id: str = "ep001") -> Dict[str, Any]:
    command = [sys.executable, str(ROOT_DIR / "tools" / "inspect_assets.py"), str(episode_dir(workspace, title, episode_id))]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(workspace))
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout or "inspect failed")
    ep_dir = episode_dir(workspace, title, episode_id)
    manifest = read_json(ep_dir / "asset_manifest.json")
    report = read_text_smart(ep_dir / "asset_report.md")
    return {"manifest": manifest, "report": report, "missing": manifest.get("summary", {}).get("missing", 0)}


def make_all(workspace: Path, title: str, idea: str, scenario: str, voice: str, burn_subtitles: bool, episode_id: str = "ep001") -> Dict[str, Any]:
    pipeline = build_pipeline(workspace, title, idea, scenario, episode_id)
    tts = synth_tts(workspace, title, voice, episode_id)
    preview = render_preview_video(workspace, title, burn_subtitles, episode_id)
    inspection = inspect_assets(workspace, title, episode_id)
    return {"pipeline": pipeline, "tts": tts, "preview": preview, "inspection": inspection}
