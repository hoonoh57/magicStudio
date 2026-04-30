from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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

HTML = '''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>magicStudio Step 1</title>
<style>
:root{--bg:#070a12;--card:#111827;--line:#2f3d5a;--text:#f5f7ff;--muted:#9caac4;--accent:#7b5cff;--good:#42d392;--warn:#ffd166;--bad:#ff6b6b}*{box-sizing:border-box}body{margin:0;background:linear-gradient(135deg,#070a12,#0e1629);color:var(--text);font-family:Segoe UI,Malgun Gothic,Apple SD Gothic Neo,sans-serif}.app{max-width:1180px;margin:0 auto;padding:24px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}.brand{font-size:28px;font-weight:900}.badge{padding:8px 12px;border-radius:999px;background:#172139;border:1px solid var(--line);color:#d9e2ff}.grid{display:grid;grid-template-columns:320px 1fr;gap:16px}.card{background:#111827;border:1px solid var(--line);border-radius:22px;overflow:hidden;box-shadow:0 22px 70px #0008}.head{padding:15px 18px;background:#172139;border-bottom:1px solid var(--line);font-weight:900}.body{padding:18px}input,textarea{width:100%;background:#080f1f;color:var(--text);border:1px solid #34455f;border-radius:14px;padding:12px;outline:none}textarea{min-height:420px;line-height:1.6;resize:vertical}label{display:block;margin:12px 0 6px;color:var(--muted);font-size:13px}button{border:0;border-radius:14px;padding:13px 14px;font-weight:850;cursor:pointer;background:#283754;color:#eef3ff}.primary{background:linear-gradient(135deg,#6c54ff,#9b78ff)}.good{background:linear-gradient(135deg,#2fd084,#80eab5);color:#06160d}.project{padding:12px;border:1px solid var(--line);border-radius:14px;background:#0b1324;margin-bottom:9px;cursor:pointer}.project.active{border-color:#8f7dff;background:#1a2542}.project b{display:block;margin-bottom:4px}.small{font-size:12px;color:var(--muted);line-height:1.5}.actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}.log{white-space:pre-wrap;background:#060b16;border:1px solid var(--line);border-radius:14px;padding:12px;min-height:150px;color:#dce6ff;margin-top:12px}.hint{padding:12px;border-radius:14px;background:#0b1324;border:1px solid var(--line);margin-bottom:12px}.debug{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:10px}.debug button{padding:10px;font-size:12px}@media(max-width:900px){.grid{grid-template-columns:1fr}.debug{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="app">
  <div class="top"><div class="brand">magicStudio</div><div class="badge" id="statusBadge">Step 1: 프로젝트/원고</div></div>
  <div class="grid">
    <section class="card">
      <div class="head">기존 프로젝트</div>
      <div class="body">
        <button id="btnRefreshProjects" type="button">프로젝트 목록 새로고침</button>
        <div class="small" style="margin:10px 0">기존 작업을 이어가려면 아래 프로젝트를 선택하세요.</div>
        <div id="projects"></div>
      </div>
    </section>
    <section class="card">
      <div class="head">새 프로젝트 / 원고 저장</div>
      <div class="body">
        <div class="hint"><b>이번 단계에서 확인할 기능은 3개뿐입니다.</b><div class="small">1) 새 프로젝트명 입력  2) 원고 작성/수정  3) 저장 후 다시 불러오기</div></div>
        <label>프로젝트명</label><input id="title" value="불법강호">
        <label>한 줄 아이디어</label><input id="idea" value="현대 서울에 깨어난 백 년 전 무인이 국가등록무림과 충돌하는 3분 시리즈">
        <label>원고</label><textarea id="scenario"></textarea>
        <div class="actions"><button id="btnSave" class="primary" type="button">프로젝트/원고 저장</button><button id="btnLoad" class="good" type="button">현재 프로젝트 불러오기</button></div>
        <div class="debug"><button id="btnPing" type="button">서버 연결 확인</button><button id="btnShowPath" type="button">저장 경로 확인</button><button id="btnClearLog" type="button">로그 지우기</button></div>
        <div id="logBox" class="log"></div>
      </div>
    </section>
  </div>
</div>
<script>
(function(){
  'use strict';
  const DEFAULT_SCENARIO = `__SCENARIO__`;
  function el(id){ return document.getElementById(id); }
  function setStatus(text){ el('statusBadge').textContent = text; }
  function logMsg(text){
    const box = el('logBox');
    box.textContent += (box.textContent ? '\n' : '') + '[' + new Date().toLocaleTimeString() + '] ' + text;
    box.scrollTop = box.scrollHeight;
  }
  function esc(text){ return String(text || '').replace(/[&<>]/g, function(m){ return {'&':'&amp;','<':'&lt;','>':'&gt;'}[m]; }); }
  function payload(){
    return {
      title: el('title').value.trim() || '새프로젝트',
      idea: el('idea').value.trim(),
      scenario: el('scenario').value
    };
  }
  async function postJson(path, data){
    const response = await fetch(path, {
      method: 'POST',
      headers: {'Content-Type': 'application/json; charset=utf-8'},
      body: JSON.stringify(data || {})
    });
    const text = await response.text();
    let json = null;
    try { json = JSON.parse(text); } catch(e) { throw new Error('JSON 응답 파싱 실패: ' + text.slice(0, 200)); }
    if(!response.ok || !json.ok){ throw new Error(json.error || ('HTTP ' + response.status)); }
    return json;
  }
  async function getJson(path){
    const response = await fetch(path, {method:'GET'});
    const text = await response.text();
    let json = null;
    try { json = JSON.parse(text); } catch(e) { throw new Error('JSON 응답 파싱 실패: ' + text.slice(0, 200)); }
    if(!response.ok || json.ok === false){ throw new Error(json.error || ('HTTP ' + response.status)); }
    return json;
  }
  async function saveProject(){
    try{
      setStatus('저장 중...');
      logMsg('저장 요청: ' + payload().title);
      const result = await postJson('/api/save', payload());
      logMsg('저장 완료: ' + result.path);
      logMsg('프로젝트 폴더: ' + result.project_root);
      setStatus('저장 완료');
      await loadProjects();
    }catch(e){
      setStatus('저장 오류');
      logMsg('저장 실패: ' + e.message);
    }
  }
  async function loadProject(){
    try{
      setStatus('불러오는 중...');
      const name = el('title').value.trim() || '새프로젝트';
      logMsg('불러오기 요청: ' + name);
      const result = await getJson('/api/project?title=' + encodeURIComponent(name));
      if(result.idea !== undefined){ el('idea').value = result.idea; }
      if(result.scenario !== undefined){ el('scenario').value = result.scenario; }
      logMsg('불러오기 완료: ' + result.title);
      logMsg('원고 길이: ' + String((result.scenario || '').length) + '자');
      setStatus('불러오기 완료');
    }catch(e){
      setStatus('불러오기 오류');
      logMsg('불러오기 실패: ' + e.message);
    }
  }
  async function loadProjects(){
    try{
      const result = await getJson('/api/projects');
      const box = el('projects');
      box.innerHTML = '';
      const current = el('title').value.trim();
      if(!result.projects || result.projects.length === 0){
        box.innerHTML = '<div class="small">아직 저장된 프로젝트가 없습니다.</div>';
        return;
      }
      result.projects.forEach(function(p){
        const div = document.createElement('div');
        div.className = 'project' + (p.title === current ? ' active' : '');
        div.innerHTML = '<b>' + esc(p.title) + '</b><div class="small">' + esc(p.path) + '</div>';
        div.addEventListener('click', async function(){
          el('title').value = p.title;
          await loadProject();
          await loadProjects();
        });
        box.appendChild(div);
      });
      logMsg('프로젝트 목록 로드: ' + result.projects.length + '개');
    }catch(e){
      logMsg('프로젝트 목록 실패: ' + e.message);
    }
  }
  async function ping(){
    try{
      const result = await getJson('/api/ping');
      logMsg('서버 연결 OK: ' + result.workspace);
      setStatus('서버 연결 OK');
    }catch(e){ logMsg('서버 연결 실패: ' + e.message); }
  }
  async function showPath(){
    try{
      const result = await getJson('/api/path?title=' + encodeURIComponent(payload().title));
      logMsg('project_root: ' + result.project_root);
      logMsg('scenario_path: ' + result.scenario_path);
    }catch(e){ logMsg('경로 확인 실패: ' + e.message); }
  }
  function bind(){
    el('scenario').value = DEFAULT_SCENARIO;
    el('btnSave').addEventListener('click', saveProject);
    el('btnLoad').addEventListener('click', loadProject);
    el('btnRefreshProjects').addEventListener('click', loadProjects);
    el('btnPing').addEventListener('click', ping);
    el('btnShowPath').addEventListener('click', showPath);
    el('btnClearLog').addEventListener('click', function(){ el('logBox').textContent = ''; });
  }
  document.addEventListener('DOMContentLoaded', async function(){
    bind();
    logMsg('화면 준비 완료');
    await ping();
    await loadProjects();
  });
})();
</script>
</body>
</html>'''.replace('__SCENARIO__', DEFAULT_SCENARIO.replace('`', '\\`'))


def read_text_smart(path: Path) -> str:
    if not path.exists():
        return ""
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return path.read_text(encoding=enc)
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


def project_root(workspace: Path, title: str) -> Path:
    return workspace / "local_projects" / safe_project_name(title)


def episode_dir(workspace: Path, title: str) -> Path:
    return project_root(workspace, title) / "episodes" / "ep001"


def safe_project_name(title: str) -> str:
    value = title.strip() or DEFAULT_TITLE
    bad_chars = '<>:"/\\|?*'
    for ch in bad_chars:
        value = value.replace(ch, '_')
    return value


def save_project(workspace: Path, title: str, idea: str, scenario: str) -> Dict[str, Any]:
    root = project_root(workspace, title)
    ep = episode_dir(workspace, title)
    root.mkdir(parents=True, exist_ok=True)
    ep.mkdir(parents=True, exist_ok=True)
    write_json(root / "project.json", {"title": title, "idea": idea, "status": "draft"})
    write_json(ep / "web_meta.json", {"title": title, "idea": idea, "scenario_path": str(ep / "scenario.md")})
    write_text_utf8(ep / "scenario.md", scenario)
    return {
        "path": str(ep / "scenario.md"),
        "project_root": str(root),
        "scenario_path": str(ep / "scenario.md"),
    }


def load_project(workspace: Path, title: str) -> Dict[str, Any]:
    root = project_root(workspace, title)
    ep = episode_dir(workspace, title)
    project = read_json(root / "project.json")
    meta = read_json(ep / "web_meta.json")
    scenario = read_text_smart(ep / "scenario.md")
    if not scenario:
        scenario = DEFAULT_SCENARIO
    return {
        "ok": True,
        "title": title,
        "idea": meta.get("idea") or project.get("idea", DEFAULT_IDEA),
        "scenario": scenario,
        "project": project,
        "project_root": str(root),
        "scenario_path": str(ep / "scenario.md"),
        "exists": root.exists(),
    }


def list_projects(workspace: Path) -> List[Dict[str, str]]:
    root = workspace / "local_projects"
    rows: List[Dict[str, str]] = []
    if not root.exists():
        return rows
    for item in sorted(root.iterdir(), key=lambda p: p.name):
        if item.is_dir():
            project = read_json(item / "project.json")
            display_title = str(project.get("title", item.name))
            rows.append({"title": display_title, "path": str(item)})
    return rows


class Handler(BaseHTTPRequestHandler):
    workspace: Path = ROOT_DIR

    def send_json(self, payload: Any, status_code: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_html(self) -> None:
        data = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self) -> Dict[str, Any]:
        size = int(self.headers.get("Content-Length", "0") or "0")
        if size <= 0:
            return {}
        raw = self.rfile.read(size).decode("utf-8")
        return json.loads(raw) if raw else {}

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                self.send_html()
            elif parsed.path == "/api/ping":
                self.send_json({"ok": True, "workspace": str(self.workspace)})
            elif parsed.path == "/api/projects":
                self.send_json({"ok": True, "projects": list_projects(self.workspace)})
            elif parsed.path == "/api/project":
                title = parse_qs(parsed.query).get("title", [DEFAULT_TITLE])[0]
                self.send_json(load_project(self.workspace, title))
            elif parsed.path == "/api/path":
                title = parse_qs(parsed.query).get("title", [DEFAULT_TITLE])[0]
                self.send_json({
                    "ok": True,
                    "project_root": str(project_root(self.workspace, title)),
                    "scenario_path": str(episode_dir(self.workspace, title) / "scenario.md"),
                })
            else:
                self.send_json({"ok": False, "error": "not found"}, 404)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, 500)

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            data = self.body()
            title = str(data.get("title", DEFAULT_TITLE)).strip() or DEFAULT_TITLE
            idea = str(data.get("idea", DEFAULT_IDEA)).strip() or DEFAULT_IDEA
            scenario = str(data.get("scenario", DEFAULT_SCENARIO)) or DEFAULT_SCENARIO
            if parsed.path == "/api/save":
                self.send_json({"ok": True, **save_project(self.workspace, title, idea, scenario)})
            else:
                self.send_json({"ok": False, "error": "not found"}, 404)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, 500)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Run magicStudio step 1 project/scenario UI")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7865)
    args = parser.parse_args()
    Handler.workspace = Path(args.workspace).resolve()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("=== magicStudio Step 1 UI ===")
    print(f"workspace: {Handler.workspace}")
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
