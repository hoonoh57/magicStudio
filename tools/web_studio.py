from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, urlparse, unquote

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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


HTML = r'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>magicStudio Control Room</title>
  <style>
    :root { --bg:#0b1020; --panel:#121a32; --panel2:#17213c; --line:#263656; --text:#eaf0ff; --muted:#8fa1c7; --accent:#7c5cff; --good:#48d597; --bad:#ff6b6b; --warn:#ffcf5c; }
    * { box-sizing:border-box; }
    body { margin:0; background:linear-gradient(135deg,#08101f,#10172a 50%,#111827); color:var(--text); font-family:Segoe UI, Pretendard, Malgun Gothic, Arial, sans-serif; }
    header { padding:18px 24px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; align-items:center; background:rgba(10,16,32,.92); position:sticky; top:0; z-index:10; }
    h1 { font-size:22px; margin:0; letter-spacing:.2px; }
    .tag { color:#c8d3ff; font-size:12px; padding:5px 10px; border:1px solid var(--line); border-radius:999px; background:#111a35; }
    main { display:grid; grid-template-columns:340px 1fr 420px; gap:14px; padding:14px; min-height:calc(100vh - 64px); }
    .card { background:rgba(18,26,50,.96); border:1px solid var(--line); border-radius:18px; box-shadow:0 18px 50px rgba(0,0,0,.22); overflow:hidden; }
    .card h2 { font-size:15px; margin:0; padding:13px 15px; border-bottom:1px solid var(--line); background:rgba(23,33,60,.75); }
    .body { padding:14px; }
    label { display:block; color:var(--muted); font-size:12px; margin:10px 0 5px; }
    input, textarea, select { width:100%; background:#0d152b; color:var(--text); border:1px solid #2b3a5d; border-radius:12px; padding:10px 11px; outline:none; }
    textarea { min-height:190px; resize:vertical; line-height:1.55; }
    button { border:0; border-radius:12px; padding:10px 12px; color:white; background:linear-gradient(135deg,#715cff,#9b6dff); cursor:pointer; font-weight:700; }
    button.secondary { background:#22304f; color:#d7e1ff; border:1px solid #34466f; }
    button.good { background:linear-gradient(135deg,#1aae74,#37d597); color:#07131c; }
    button.warn { background:linear-gradient(135deg,#ffb84d,#ffdf7b); color:#1b1606; }
    button.danger { background:linear-gradient(135deg,#e04b5f,#ff7a7a); }
    .row { display:flex; gap:8px; align-items:center; }
    .row > * { flex:1; }
    .stack { display:grid; gap:8px; }
    .project { padding:10px; border:1px solid var(--line); border-radius:12px; margin-bottom:8px; background:#0f1930; cursor:pointer; }
    .project.active { border-color:#8f7bff; background:#182447; }
    .small { font-size:12px; color:var(--muted); }
    .pill { display:inline-flex; gap:6px; align-items:center; padding:5px 8px; border-radius:999px; background:#0d152b; border:1px solid var(--line); color:#cbd7ff; font-size:12px; margin:2px; }
    .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
    .tabs { display:flex; gap:8px; padding:10px; border-bottom:1px solid var(--line); background:#0f1831; flex-wrap:wrap; }
    .tabs button { padding:8px 10px; background:#1b2848; }
    .tabs button.active { background:#7c5cff; }
    pre { white-space:pre-wrap; word-break:break-word; background:#081022; border:1px solid #263656; border-radius:12px; padding:12px; max-height:420px; overflow:auto; color:#dfe7ff; }
    .assetRow { display:grid; grid-template-columns:90px 1fr 55px 80px; gap:8px; padding:8px; border-bottom:1px solid #243352; font-size:12px; align-items:center; }
    .ok { color:var(--good); font-weight:700; } .no { color:var(--bad); font-weight:700; }
    video { width:100%; border-radius:14px; border:1px solid var(--line); background:#050815; }
    .log { min-height:160px; max-height:260px; overflow:auto; background:#070d1d; color:#cfe0ff; }
    .cmd { min-height:82px; }
    .kbd { font-family:Consolas, monospace; color:#fff; background:#202b49; padding:2px 6px; border-radius:6px; }
    @media (max-width:1200px){ main{ grid-template-columns:1fr; } }
  </style>
</head>
<body>
<header>
  <h1>magicStudio Control Room</h1>
  <div class="tag">Prompt CRUD · Project · Scenario · Assets · Preview</div>
</header>
<main>
  <section class="card">
    <h2>프로젝트</h2>
    <div class="body stack">
      <button class="good" onclick="newProjectFromFields()">현재 입력으로 프로젝트 생성/재생성</button>
      <button class="secondary" onclick="loadProjects()">프로젝트 새로고침</button>
      <div id="projects"></div>
    </div>
  </section>

  <section class="card">
    <div class="tabs">
      <button id="tab_editor" class="active" onclick="showTab('editor')">원고/프롬프트</button>
      <button id="tab_assets" onclick="showTab('assets')">자산</button>
      <button id="tab_preview" onclick="showTab('preview')">프리뷰</button>
      <button id="tab_report" onclick="showTab('report')">리포트</button>
    </div>
    <div class="body" id="view_editor">
      <div class="grid2">
        <div><label>제목</label><input id="title" value="불법강호" /></div>
        <div><label>아이디어</label><input id="idea" value="현대 서울에 깨어난 백 년 전 무인이 국가등록무림과 충돌하는 3분 시리즈" /></div>
      </div>
      <label>시나리오 Markdown</label>
      <textarea id="scenario"></textarea>
      <div class="row" style="margin-top:10px">
        <button onclick="saveScenario()">시나리오 저장</button>
        <button class="secondary" onclick="runPipeline()">제작계획 재생성</button>
        <button class="warn" onclick="ttsRenderInspect()">TTS+렌더+검수</button>
      </div>
      <label>Keyframe Prompt 선택</label>
      <select id="promptSelect" onchange="loadPromptIntoEditor()"></select>
      <textarea id="promptEditor" style="min-height:110px"></textarea>
      <div class="row" style="margin-top:8px">
        <button onclick="savePrompt()">프롬프트 수정 저장</button>
        <button class="secondary" onclick="refreshProject()">다시 읽기</button>
      </div>
    </div>

    <div class="body" id="view_assets" style="display:none">
      <div id="assetSummary" class="small"></div>
      <div id="assets"></div>
    </div>

    <div class="body" id="view_preview" style="display:none">
      <video id="video" controls></video>
      <div class="row" style="margin-top:10px">
        <button onclick="renderPreview()">프리뷰 렌더</button>
        <button class="secondary" onclick="openPreviewFile()">MP4 경로 표시</button>
      </div>
      <pre id="previewInfo"></pre>
    </div>

    <div class="body" id="view_report" style="display:none">
      <button onclick="inspectAssets()">asset_report.md 생성/갱신</button>
      <pre id="report"></pre>
    </div>
  </section>

  <section class="card">
    <h2>프롬프트 명령창</h2>
    <div class="body stack">
      <div class="small">예: <span class="kbd">프로젝트 생성</span>, <span class="kbd">시나리오 저장</span>, <span class="kbd">프리뷰 렌더</span>, <span class="kbd">검수</span>, <span class="kbd">전체 제작</span></div>
      <textarea id="command" class="cmd" placeholder="자연어로 명령하세요. 예) 현재 원고로 전체 제작하고 프리뷰까지 만들어줘"></textarea>
      <button class="good" onclick="runCommand()">명령 실행</button>
      <pre id="log" class="log"></pre>
    </div>
  </section>
</main>
<script>
let state = { project:null, promptData:null };
document.getElementById('scenario').value = `__DEFAULT_SCENARIO__`;

function showTab(name){
  ['editor','assets','preview','report'].forEach(x=>{
    document.getElementById('view_'+x).style.display = x===name ? 'block':'none';
    document.getElementById('tab_'+x).classList.toggle('active', x===name);
  });
}
function log(msg){ const el=document.getElementById('log'); el.textContent += '\n' + msg; el.scrollTop=el.scrollHeight; }
async function api(path, data){
  const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data||{})});
  const j = await res.json(); if(!j.ok){ throw new Error(j.error || 'API error'); } return j;
}
async function getJson(path){ const r=await fetch(path); return await r.json(); }
function formPayload(){ return {title:title.value.trim(), idea:idea.value.trim(), scenario:scenario.value}; }
async function loadProjects(){
  const j=await getJson('/api/projects');
  const box=document.getElementById('projects'); box.innerHTML='';
  j.projects.forEach(p=>{
    const div=document.createElement('div'); div.className='project'+(state.project===p.title?' active':'');
    div.innerHTML=`<b>${p.title}</b><div class="small">${p.path}</div><div class="small">${p.status||''}</div>`;
    div.onclick=()=>selectProject(p.title); box.appendChild(div);
  });
}
async function selectProject(name){ state.project=name; title.value=name; await refreshProject(); await loadProjects(); }
async function refreshProject(){
  if(!title.value.trim()) return;
  const j=await getJson('/api/project?title='+encodeURIComponent(title.value.trim()));
  if(j.scenario) scenario.value=j.scenario;
  if(j.idea) idea.value=j.idea;
  state.promptData=j.keyframe_prompts || null;
  fillPrompts(); renderAssets(j.asset_manifest); renderReport(j.asset_report || ''); setPreview(j.preview_url, j.preview_result);
}
function fillPrompts(){
  const sel=document.getElementById('promptSelect'); sel.innerHTML='';
  const arr=(state.promptData&&state.promptData.prompts)||[];
  arr.forEach((p,i)=>{ const o=document.createElement('option'); o.value=i; o.textContent=`${i+1}. ${p.scene_title} / ${p.keyframe_id}`; sel.appendChild(o); });
  loadPromptIntoEditor();
}
function loadPromptIntoEditor(){
  const arr=(state.promptData&&state.promptData.prompts)||[]; const i=Number(promptSelect.value||0);
  promptEditor.value=arr[i]?arr[i].prompt:'';
}
async function savePrompt(){
  const i=Number(promptSelect.value||0); const arr=(state.promptData&&state.promptData.prompts)||[];
  if(!arr[i]) return;
  const j=await api('/api/prompt/update',{title:title.value.trim(), index:i, prompt:promptEditor.value});
  log('프롬프트 저장: '+j.path); await refreshProject();
}
async function newProjectFromFields(){ const j=await api('/api/pipeline/run', formPayload()); log('프로젝트 생성: '+j.project_root); state.project=title.value.trim(); await refreshProject(); await loadProjects(); }
async function runPipeline(){ const j=await api('/api/pipeline/run', formPayload()); log('제작계획 재생성: '+j.episode_dir); await refreshProject(); }
async function saveScenario(){ const j=await api('/api/scenario/save', formPayload()); log('시나리오 저장: '+j.path); await refreshProject(); }
async function synthTTS(){ const j=await api('/api/tts/synth',{title:title.value.trim(), voice:'Microsoft Heami Desktop'}); log('TTS: '+j.ok_count+'/'+j.total); await refreshProject(); }
async function renderPreview(){ const j=await api('/api/preview/render',{title:title.value.trim(), burn_subtitles:true}); log('렌더: '+j.mode); await refreshProject(); }
async function inspectAssets(){ const j=await api('/api/assets/inspect',{title:title.value.trim()}); log('검수: missing '+j.missing); document.getElementById('report').textContent=j.report||''; await refreshProject(); }
async function ttsRenderInspect(){ await synthTTS(); await renderPreview(); await inspectAssets(); }
async function runCommand(){
  const cmd=command.value.trim(); if(!cmd) return;
  const j=await api('/api/command',{command:cmd, ...formPayload()});
  log('명령결과: '+j.message); await refreshProject(); await loadProjects();
}
function renderAssets(manifest){
  const s=document.getElementById('assetSummary'); const box=document.getElementById('assets'); box.innerHTML='';
  if(!manifest){ s.textContent='asset_manifest 없음'; return; }
  const sum=manifest.summary||{}; s.innerHTML=`<span class="pill">existing ${sum.existing}/${sum.total}</span><span class="pill">missing ${sum.missing}</span>`;
  (manifest.assets||[]).forEach(a=>{ const d=document.createElement('div'); d.className='assetRow'; d.innerHTML=`<div>${a.asset_type}</div><div>${a.relative_path}</div><div class="${a.exists?'ok':'no'}">${a.exists?'YES':'NO'}</div><div>${a.size_bytes}</div>`; box.appendChild(d); });
}
function renderReport(txt){ report.textContent=txt||''; }
function setPreview(url, result){
  const v=document.getElementById('video'); if(url){ v.src=url+'?t='+Date.now(); }
  previewInfo.textContent=result?JSON.stringify(result,null,2):'';
}
function openPreviewFile(){ log('preview: local_projects\\'+title.value.trim()+'\\episodes\\ep001\\preview\\preview.mp4'); }
loadProjects();
</script>
</body>
</html>'''.replace('__DEFAULT_SCENARIO__', DEFAULT_SCENARIO.replace('`','\\`'))


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def project_root(workspace: Path, title: str) -> Path:
    return workspace / "local_projects" / title


def episode_dir(workspace: Path, title: str) -> Path:
    return project_root(workspace, title) / "episodes" / "ep001"


def run_pipeline(workspace: Path, title: str, idea: str, scenario: str) -> Dict[str, Any]:
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
    ProductionPlanner().save_all(vml_episode, timeline, ep_dir)
    preview_plan = read_json(ep_dir / "preview_render_plan.json", {})
    tts_script = read_json(ep_dir / "tts_script.json", {})
    asset_manifest = AssetRegistry().build_and_save(ep_dir, vml_episode, preview_plan, tts_script, None)
    return {"project_id": project.project_id, "project_root": str(project.root_path), "episode_dir": str(ep_dir), "asset_manifest": asset_manifest}


def save_scenario(workspace: Path, title: str, idea: str, scenario: str) -> Dict[str, Any]:
    ep_dir = episode_dir(workspace, title)
    path = ep_dir / "scenario.md"
    write_text(path, scenario)
    meta = {"title": title, "idea": idea, "scenario_path": str(path)}
    write_json(ep_dir / "web_meta.json", meta)
    return {"path": str(path)}


def load_project_payload(workspace: Path, title: str) -> Dict[str, Any]:
    ep_dir = episode_dir(workspace, title)
    root = project_root(workspace, title)
    meta = read_json(ep_dir / "web_meta.json", {}) or {}
    project = read_json(root / "project.json", {}) or {}
    scenario_text = ""
    for candidate in [ep_dir / "scenario.md", ep_dir / "scenario.txt"]:
        if candidate.exists():
            scenario_text = candidate.read_text(encoding="utf-8")
            break
    if not scenario_text:
        # Fall back to default so the browser is immediately editable.
        scenario_text = DEFAULT_SCENARIO
    preview_result = read_json(ep_dir / "preview" / "preview_render_result.json", None)
    report_path = ep_dir / "asset_report.md"
    return {
        "ok": True,
        "title": title,
        "idea": meta.get("idea") or project.get("idea", DEFAULT_IDEA),
        "scenario": scenario_text,
        "project": project,
        "keyframe_prompts": read_json(ep_dir / "keyframe_prompts.json", None),
        "asset_manifest": read_json(ep_dir / "asset_manifest.json", None),
        "preview_result": preview_result,
        "preview_url": f"/media/{title}/episodes/ep001/preview/preview.mp4" if (ep_dir / "preview" / "preview.mp4").exists() else "",
        "asset_report": report_path.read_text(encoding="utf-8") if report_path.exists() else "",
    }


def synth_tts(workspace: Path, title: str, voice: str) -> Dict[str, Any]:
    cmd = [sys.executable, str(ROOT_DIR / "tools" / "synth_tts_windows.py"), str(episode_dir(workspace, title)), "--voice", voice]
    completed = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(workspace))
    result_path = episode_dir(workspace, title) / "audio" / "tts_synthesis_result.json"
    payload = read_json(result_path, {}) or {}
    payload["returncode"] = completed.returncode
    payload["stdout"] = completed.stdout
    payload["stderr"] = completed.stderr
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout or "TTS failed")
    return payload


def render_preview(workspace: Path, title: str, burn_subtitles: bool = True) -> Dict[str, Any]:
    renderer = FfmpegPreviewRenderer(burn_subtitles=burn_subtitles)
    result = renderer.render_from_file(episode_dir(workspace, title))
    ep_dir = episode_dir(workspace, title)
    vml = read_json(ep_dir / "vml_scenes.json", {})
    preview_plan = read_json(ep_dir / "preview_render_plan.json", {})
    tts_script = read_json(ep_dir / "tts_script.json", {})
    AssetRegistry().build_and_save(ep_dir, vml, preview_plan, tts_script, result)
    return result


def inspect_assets(workspace: Path, title: str) -> Dict[str, Any]:
    cmd = [sys.executable, str(ROOT_DIR / "tools" / "inspect_assets.py"), str(episode_dir(workspace, title))]
    completed = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(workspace))
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout or "inspect failed")
    ep_dir = episode_dir(workspace, title)
    manifest = read_json(ep_dir / "asset_manifest.json", {}) or {}
    report_path = ep_dir / "asset_report.md"
    return {
        "stdout": completed.stdout,
        "manifest": manifest,
        "report": report_path.read_text(encoding="utf-8") if report_path.exists() else "",
        "missing": manifest.get("summary", {}).get("missing", 0),
    }


def update_prompt(workspace: Path, title: str, index: int, prompt: str) -> Dict[str, Any]:
    path = episode_dir(workspace, title) / "keyframe_prompts.json"
    payload = read_json(path, None)
    if not payload or "prompts" not in payload:
        raise FileNotFoundError("keyframe_prompts.json not found")
    prompts = payload.get("prompts", [])
    if index < 0 or index >= len(prompts):
        raise IndexError("prompt index out of range")
    prompts[index]["prompt"] = prompt
    write_json(path, payload)
    return {"path": str(path), "index": index}


def list_projects(workspace: Path) -> List[Dict[str, Any]]:
    root = workspace / "local_projects"
    result: List[Dict[str, Any]] = []
    if not root.exists():
        return result
    for item in sorted(root.iterdir(), key=lambda p: p.name):
        if not item.is_dir():
            continue
        ep = item / "episodes" / "ep001"
        manifest = read_json(ep / "asset_manifest.json", {}) or {}
        status = ""
        if manifest:
            s = manifest.get("summary", {})
            status = f"assets {s.get('existing', 0)}/{s.get('total', 0)} missing {s.get('missing', 0)}"
        result.append({"title": item.name, "path": str(item), "status": status})
    return result


class StudioHandler(BaseHTTPRequestHandler):
    workspace: Path = ROOT_DIR

    def _json(self, payload: Any, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html(self) -> None:
        data = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                self._html()
            elif parsed.path == "/api/projects":
                self._json({"ok": True, "projects": list_projects(self.workspace)})
            elif parsed.path == "/api/project":
                qs = parse_qs(parsed.query)
                title = qs.get("title", [""])[0]
                self._json(load_project_payload(self.workspace, title))
            elif parsed.path.startswith("/media/"):
                self._serve_media(parsed.path)
            else:
                self._json({"ok": False, "error": "not found"}, 404)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    def do_POST(self) -> None:
        try:
            body = self._read_body()
            path = urlparse(self.path).path
            title = str(body.get("title", "불법강호")).strip() or "불법강호"
            idea = str(body.get("idea", DEFAULT_IDEA)).strip() or DEFAULT_IDEA
            scenario = str(body.get("scenario", DEFAULT_SCENARIO)) or DEFAULT_SCENARIO
            if path == "/api/pipeline/run":
                save_scenario(self.workspace, title, idea, scenario)
                self._json({"ok": True, **run_pipeline(self.workspace, title, idea, scenario)})
            elif path == "/api/scenario/save":
                self._json({"ok": True, **save_scenario(self.workspace, title, idea, scenario)})
            elif path == "/api/tts/synth":
                self._json({"ok": True, **synth_tts(self.workspace, title, str(body.get("voice", "Microsoft Heami Desktop")))})
            elif path == "/api/preview/render":
                self._json({"ok": True, **render_preview(self.workspace, title, bool(body.get("burn_subtitles", True)))})
            elif path == "/api/assets/inspect":
                self._json({"ok": True, **inspect_assets(self.workspace, title)})
            elif path == "/api/prompt/update":
                self._json({"ok": True, **update_prompt(self.workspace, title, int(body.get("index", 0)), str(body.get("prompt", "")))})
            elif path == "/api/command":
                self._json({"ok": True, **self._run_command(body)})
            else:
                self._json({"ok": False, "error": "not found"}, 404)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    def _run_command(self, body: Dict[str, Any]) -> Dict[str, Any]:
        cmd = str(body.get("command", "")).strip()
        title = str(body.get("title", "불법강호")).strip() or "불법강호"
        idea = str(body.get("idea", DEFAULT_IDEA)).strip() or DEFAULT_IDEA
        scenario = str(body.get("scenario", DEFAULT_SCENARIO)) or DEFAULT_SCENARIO
        low = cmd.lower()
        if any(k in cmd for k in ["전체", "끝까지", "프리뷰까지", "제작"]):
            save_scenario(self.workspace, title, idea, scenario)
            run_pipeline(self.workspace, title, idea, scenario)
            synth_tts(self.workspace, title, "Microsoft Heami Desktop")
            render_preview(self.workspace, title, True)
            inspect_assets(self.workspace, title)
            return {"message": "전체 제작 완료: 계획/TTS/프리뷰/검수"}
        if any(k in cmd for k in ["프로젝트", "생성", "재생성"]):
            save_scenario(self.workspace, title, idea, scenario)
            run_pipeline(self.workspace, title, idea, scenario)
            return {"message": "프로젝트/제작계획 생성 완료"}
        if any(k in cmd for k in ["시나리오", "원고", "저장"]):
            save_scenario(self.workspace, title, idea, scenario)
            return {"message": "시나리오 저장 완료"}
        if "tts" in low or "음성" in cmd or "내레이션" in cmd:
            synth_tts(self.workspace, title, "Microsoft Heami Desktop")
            return {"message": "TTS 생성 완료"}
        if "렌더" in cmd or "프리뷰" in cmd or "mp4" in low:
            render_preview(self.workspace, title, True)
            return {"message": "프리뷰 렌더 완료"}
        if "검수" in cmd or "자산" in cmd or "리포트" in cmd:
            inspect_assets(self.workspace, title)
            return {"message": "자산 검수 완료"}
        return {"message": "명령을 실행할 수 있는 형태로 해석하지 못했습니다. 예: 전체 제작, 프리뷰 렌더, 검수"}

    def _serve_media(self, url_path: str) -> None:
        rel = unquote(url_path[len("/media/"):])
        path = (self.workspace / "local_projects" / rel).resolve()
        root = (self.workspace / "local_projects").resolve()
        if not str(path).startswith(str(root)) or not path.exists() or not path.is_file():
            self.send_response(404); self.end_headers(); return
        content_type = "video/mp4" if path.suffix.lower() == ".mp4" else "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Run magicStudio browser control room.")
    parser.add_argument("--workspace", default=".", help="Workspace root. Default: current directory")
    parser.add_argument("--host", default="127.0.0.1", help="Host. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=7861, help="Port. Default: 7861")
    args = parser.parse_args()
    StudioHandler.workspace = Path(args.workspace).resolve()
    server = ThreadingHTTPServer((args.host, args.port), StudioHandler)
    print("=== magicStudio Web Control Room ===")
    print(f"workspace: {StudioHandler.workspace}")
    print(f"url: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutdown")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
