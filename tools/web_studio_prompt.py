from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT_DIR / "tools"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from web_studio import DEFAULT_IDEA, DEFAULT_SCENARIO, inspect_assets, list_projects, load_project_payload, render_preview, run_pipeline, save_scenario, synth_tts

HTML = '''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>magicStudio Prompt UI</title><style>
body{margin:0;background:#080c16;color:#eef3ff;font-family:Segoe UI,Malgun Gothic,sans-serif} .wrap{max-width:1180px;margin:0 auto;padding:24px 18px 100px} header{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}.brand{font-size:26px;font-weight:900}.pill{background:#17223a;border:1px solid #2b3b5c;border-radius:999px;padding:7px 12px;color:#bfcbe4;font-size:12px}.hero{display:grid;grid-template-columns:1fr 420px;gap:16px}.card{background:#111827;border:1px solid #2b3b5c;border-radius:22px;overflow:hidden;box-shadow:0 24px 80px #0008}.head{padding:15px 18px;background:#17223a;border-bottom:1px solid #2b3b5c;font-weight:800}.body{padding:18px}.row{display:grid;grid-template-columns:220px 1fr;gap:10px}.actions{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:12px}input,textarea,select{width:100%;box-sizing:border-box;background:#090f1f;color:#eef3ff;border:1px solid #334563;border-radius:14px;padding:12px;outline:none}textarea{min-height:160px;line-height:1.55;resize:vertical}.prompt{font-size:18px;min-height:132px}button{border:0;border-radius:14px;background:#293855;color:#eef3ff;font-weight:800;padding:13px;cursor:pointer}.primary{background:#765cff}.good{background:#35d08a;color:#06160d}.warn{background:#ffd166;color:#201600}.grid{display:grid;grid-template-columns:260px 1fr 320px;gap:16px;margin-top:16px}.project{background:#0c1324;border:1px solid #2b3b5c;border-radius:14px;padding:11px;margin-bottom:9px;cursor:pointer}.project b{display:block}.small{color:#99a9c6;font-size:12px}.step{display:flex;justify-content:space-between;gap:10px;padding:12px;border:1px solid #2b3b5c;border-radius:14px;background:#0c1324;margin-bottom:9px}.dot{width:12px;height:12px;border-radius:50%;background:#ffd166}.dot.ok{background:#35d08a}video{width:100%;border-radius:16px;border:1px solid #2b3b5c;background:#000}.log{height:210px;overflow:auto;white-space:pre-wrap;background:#070b14;border:1px solid #2b3b5c;border-radius:14px;padding:12px}.bar{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);width:min(900px,calc(100vw - 28px));display:grid;grid-template-columns:1fr 130px;gap:10px;background:#111827;border:1px solid #2b3b5c;border-radius:22px;padding:12px;box-shadow:0 20px 70px #000a}@media(max-width:1050px){.hero,.grid{grid-template-columns:1fr}.row{grid-template-columns:1fr}}
</style></head><body><div class="wrap"><header><div class="brand">magicStudio</div><div><span class="pill" id="assetState">대기</span> <button onclick="toggleSettings()">설정</button></div></header><section class="hero"><div class="card"><div class="head">프롬프트로 제작</div><div class="body"><div class="row"><input id="title" value="불법강호" placeholder="프로젝트명"><input id="idea" value="현대 서울에 깨어난 백 년 전 무인이 국가등록무림과 충돌하는 3분 시리즈" placeholder="아이디어"></div><textarea id="mainPrompt" class="prompt">현재 원고로 전체 제작하고, 한국어 TTS와 자막이 들어간 프리뷰 영상을 만들어줘.</textarea><div class="actions"><button class="primary" onclick="makeAll()">전체 자동 제작</button><button onclick="planOnly()">계획만</button><button class="warn" onclick="previewOnly()">프리뷰</button></div></div></div><div class="card"><div class="head">프리뷰</div><div class="body"><video id="video" controls></video><div id="previewInfo" class="small">아직 프리뷰가 없습니다.</div></div></div></section><section class="grid"><div class="card"><div class="head">프로젝트</div><div class="body"><button onclick="loadProjects()">새로고침</button><div id="projects" style="margin-top:12px"></div></div></div><div class="card"><div class="head">원고</div><div class="body"><textarea id="scenario"></textarea><div class="actions"><button onclick="saveDraft()">저장</button><button onclick="inspectOnly()">검수</button><button onclick="openPromptData()">프롬프트 보기</button></div></div></div><div class="card"><div class="head">상태</div><div class="body"><div id="steps"></div></div></div></section><section class="grid" style="grid-template-columns:1fr 1fr"><div class="card"><div class="head">로그</div><div class="body"><div id="log" class="log"></div></div></div><div class="card"><div class="head">상세</div><div class="body"><pre id="detail" class="log"></pre></div></div></section></div><div class="bar"><input id="quick" placeholder="예: 이 원고로 쇼츠 프리뷰까지 자동 제작해줘"><button class="good" onclick="quickRun()">실행</button></div><div id="settings" style="display:none;position:fixed;right:18px;top:70px;width:340px;background:#111827;border:1px solid #2b3b5c;border-radius:20px;padding:16px"><b>설정</b><p class="small">필요할 때만 조정합니다.</p><label>음성</label><select id="voice"><option>Microsoft Heami Desktop</option><option>Microsoft Zira Desktop</option><option>Microsoft David Desktop</option></select><label>자막</label><select id="burn"><option value="true">영상에 입히기</option><option value="false">자막 파일만</option></select><p><button onclick="toggleSettings()">닫기</button></p></div><script>
const DEFAULT_SCENARIO=`__SCENARIO__`; let active='불법강호'; scenario.value=DEFAULT_SCENARIO; function logMsg(s){log.textContent+=(log.textContent?'\n':'')+'['+new Date().toLocaleTimeString()+'] '+s;log.scrollTop=log.scrollHeight} function toggleSettings(){settings.style.display=settings.style.display==='none'?'block':'none'} async function api(p,d){const r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json; charset=utf-8'},body:JSON.stringify(d||{})});const j=await r.json();if(!j.ok)throw new Error(j.error||'실패');return j} async function getJson(p){const r=await fetch(p);return await r.json()} function data(){return{title:title.value.trim()||'불법강호',idea:idea.value.trim(),scenario:scenario.value,command:mainPrompt.value,voice:voice.value,burn_subtitles:burn.value==='true'}} async function loadProjects(){const j=await getJson('/api/projects');projects.innerHTML='';(j.projects||[]).forEach(p=>{const d=document.createElement('div');d.className='project';d.innerHTML='<b>'+esc(p.title)+'</b><span class="small">'+esc(p.status||'대기')+'</span>';d.onclick=()=>selectProject(p.title);projects.appendChild(d)})} async function selectProject(t){active=t;title.value=t;await refresh()} async function refresh(){const j=await getJson('/api/project?title='+encodeURIComponent(title.value.trim()||'불법강호'));if(j.scenario)scenario.value=j.scenario;if(j.idea)idea.value=j.idea;renderStatus(j);if(j.preview_url){video.src=j.preview_url+'?t='+Date.now();previewInfo.textContent='프리뷰 준비 완료'}detail.textContent=JSON.stringify({preview:j.preview_result,asset:j.asset_manifest&&j.asset_manifest.summary},null,2)} function renderStatus(j){const s=(j.asset_manifest&&j.asset_manifest.summary)||{};assetState.textContent=s.total?'자산 '+s.existing+'/'+s.total+' · 누락 '+s.missing:'대기';const audio=(j.preview_result&&j.preview_result.audio)||{};const rows=[['제작계획',!!j.keyframe_prompts],['자막/프리뷰',!!j.preview_url],['이미지',s.total&&s.missing===0],['한국어 TTS',audio.used_real_audio_count>0],['검수',s.total&&s.missing===0]];steps.innerHTML='';rows.forEach(r=>{const d=document.createElement('div');d.className='step';d.innerHTML='<span>'+r[0]+'</span><span class="dot '+(r[1]?'ok':'')+'"></span>';steps.appendChild(d)})} async function makeAll(){logMsg('전체 자동 제작 시작');const j=await api('/api/command',{...data(),command:'전체 제작'});logMsg(j.message);await refresh();await loadProjects()} async function planOnly(){const j=await api('/api/pipeline/run',data());logMsg('계획 생성 완료');await refresh();await loadProjects()} async function previewOnly(){const j=await api('/api/preview/render',data());logMsg(j.mode);await refresh()} async function saveDraft(){const j=await api('/api/scenario/save',data());logMsg('원고 저장');await refresh()} async function inspectOnly(){const j=await api('/api/assets/inspect',data());logMsg('검수 완료 · 누락 '+j.missing);detail.textContent=j.report||'';await refresh()} async function quickRun(){if(!quick.value.trim())return;mainPrompt.value=quick.value;const j=await api('/api/command',{...data(),command:quick.value});logMsg(j.message);await refresh();await loadProjects()} async function openPromptData(){const j=await getJson('/api/project?title='+encodeURIComponent(title.value.trim()||'불법강호'));detail.textContent=JSON.stringify(j.keyframe_prompts||{},null,2)} function esc(s){return String(s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]))} loadProjects().then(refresh).catch(e=>logMsg(e.message));
</script></body></html>'''.replace('__SCENARIO__', DEFAULT_SCENARIO.replace('`', '\\`'))


class Handler(BaseHTTPRequestHandler):
    workspace: Path = ROOT_DIR
    def json(self, payload: Any, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def html(self) -> None:
        data = HTML.encode('utf-8')
        self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def body(self) -> Dict[str, Any]:
        n = int(self.headers.get('Content-Length','0') or '0')
        return json.loads(self.rfile.read(n).decode('utf-8')) if n else {}
    def do_GET(self) -> None:
        p = urlparse(self.path)
        try:
            if p.path == '/': self.html()
            elif p.path == '/api/projects': self.json({'ok':True,'projects':list_projects(self.workspace)})
            elif p.path == '/api/project': self.json(load_project_payload(self.workspace, parse_qs(p.query).get('title',['불법강호'])[0]))
            elif p.path.startswith('/media/'): self.media(p.path)
            else: self.json({'ok':False,'error':'not found'},404)
        except Exception as e: self.json({'ok':False,'error':str(e)},500)
    def do_POST(self) -> None:
        try:
            b=self.body(); p=urlparse(self.path).path; title=str(b.get('title','불법강호')).strip() or '불법강호'; idea=str(b.get('idea',DEFAULT_IDEA)).strip() or DEFAULT_IDEA; scenario=str(b.get('scenario',DEFAULT_SCENARIO)) or DEFAULT_SCENARIO
            if p == '/api/scenario/save': self.json({'ok':True,**save_scenario(self.workspace,title,idea,scenario)})
            elif p == '/api/pipeline/run': save_scenario(self.workspace,title,idea,scenario); self.json({'ok':True,**run_pipeline(self.workspace,title,idea,scenario)})
            elif p == '/api/preview/render': self.json({'ok':True,**render_preview(self.workspace,title,bool(b.get('burn_subtitles',True)))})
            elif p == '/api/assets/inspect': self.json({'ok':True,**inspect_assets(self.workspace,title)})
            elif p == '/api/command': self.json({'ok':True,**self.command(b,title,idea,scenario)})
            else: self.json({'ok':False,'error':'not found'},404)
        except Exception as e: self.json({'ok':False,'error':str(e)},500)
    def command(self,b:Dict[str,Any],title:str,idea:str,scenario:str)->Dict[str,Any]:
        cmd=str(b.get('command','')).lower(); save_scenario(self.workspace,title,idea,scenario)
        if any(k in cmd for k in ['전체','제작','만들','프리뷰','영상','쇼츠']):
            run_pipeline(self.workspace,title,idea,scenario); synth_tts(self.workspace,title,str(b.get('voice','Microsoft Heami Desktop'))); render_preview(self.workspace,title,bool(b.get('burn_subtitles',True))); inspect_assets(self.workspace,title); return {'message':'전체 자동 제작 완료'}
        if any(k in cmd for k in ['계획','분석','장면']): run_pipeline(self.workspace,title,idea,scenario); return {'message':'제작계획 생성 완료'}
        if any(k in cmd for k in ['검수','자산','리포트']): inspect_assets(self.workspace,title); return {'message':'자산 검수 완료'}
        return {'message':'원고 저장 완료'}
    def media(self, path_text: str) -> None:
        rel = path_text[len('/media/'):]
        path = (self.workspace / 'local_projects' / rel).resolve(); root=(self.workspace/'local_projects').resolve()
        if not str(path).startswith(str(root)) or not path.exists(): self.send_response(404); self.end_headers(); return
        data=path.read_bytes(); self.send_response(200); self.send_header('Content-Type','video/mp4'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def log_message(self, format: str, *args: Any) -> None: return


def main() -> int:
    parser = argparse.ArgumentParser(description='Run prompt-first magicStudio UI')
    parser.add_argument('--workspace', default='.')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=7862)
    args = parser.parse_args(); Handler.workspace=Path(args.workspace).resolve()
    server=ThreadingHTTPServer((args.host,args.port),Handler)
    print('=== magicStudio Prompt UI ==='); print(f'workspace: {Handler.workspace}'); print(f'url: http://{args.host}:{args.port}')
    try: server.serve_forever()
    except KeyboardInterrupt: print('\nshutdown')
    finally: server.server_close()
    return 0

if __name__ == '__main__': raise SystemExit(main())
