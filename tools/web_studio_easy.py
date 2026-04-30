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

from web_studio import DEFAULT_IDEA, DEFAULT_SCENARIO, inspect_assets, load_project_payload, render_preview, run_pipeline, save_scenario, synth_tts

HTML = '''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>magicStudio Easy</title>
<style>
:root{--bg:#070a12;--card:#12192a;--card2:#172139;--line:#2d3a58;--text:#f5f7ff;--muted:#9ba9c2;--accent:#795cff;--good:#42d392;--warn:#ffd166;--bad:#ff6b6b}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 30% 0,#202a46,#070a12 45%,#03050a);color:var(--text);font-family:Segoe UI,Malgun Gothic,Apple SD Gothic Neo,sans-serif}.app{max-width:1160px;margin:0 auto;padding:28px 18px 80px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:26px}.brand{font-size:28px;font-weight:900}.badge{font-size:13px;color:#d9e2ff;background:#16213a;border:1px solid var(--line);padding:8px 13px;border-radius:999px}.hero{background:linear-gradient(180deg,#151f36,#101827);border:1px solid var(--line);border-radius:30px;padding:26px;box-shadow:0 30px 90px #0008}.hero h1{font-size:30px;margin:0 0 8px}.sub{color:var(--muted);margin-bottom:18px}.prompt{width:100%;min-height:160px;background:#070d1c;color:var(--text);border:1px solid #344563;border-radius:24px;padding:22px;font-size:21px;line-height:1.55;resize:vertical;outline:none}button{border:0;border-radius:18px;padding:16px 18px;font-weight:900;cursor:pointer;background:#2a3653;color:#eef3ff}.make{width:100%;font-size:20px;background:linear-gradient(135deg,#725cff,#a784ff);margin-top:14px}.row{display:grid;grid-template-columns:240px 1fr;gap:10px;margin-bottom:12px}input{width:100%;background:#070d1c;color:var(--text);border:1px solid #344563;border-radius:16px;padding:13px}.quick{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:12px}.grid{display:grid;grid-template-columns:1fr 380px;gap:16px;margin-top:16px}.card{background:rgba(18,25,42,.96);border:1px solid var(--line);border-radius:24px;overflow:hidden}.head{padding:15px 18px;border-bottom:1px solid var(--line);background:#172139;font-weight:900}.body{padding:18px}.steps{display:grid;gap:10px}.step{display:flex;justify-content:space-between;align-items:center;background:#0b1222;border:1px solid var(--line);border-radius:16px;padding:13px}.dot{width:13px;height:13px;border-radius:50%;background:var(--warn)}.dot.ok{background:var(--good)}video{width:100%;border-radius:18px;background:#000;border:1px solid var(--line)}.log{white-space:pre-wrap;background:#060b16;border:1px solid var(--line);border-radius:18px;min-height:170px;max-height:300px;overflow:auto;padding:14px;color:#dce6ff}.advanced{display:none;margin-top:16px}.advanced.show{display:block}textarea.script{width:100%;min-height:260px;background:#070d1c;color:#eef3ff;border:1px solid #344563;border-radius:20px;padding:16px;line-height:1.6;resize:vertical}.small{font-size:13px;color:var(--muted)}.settings{display:none;position:fixed;right:22px;top:80px;width:360px;background:#111827;border:1px solid var(--line);border-radius:24px;padding:18px;box-shadow:0 25px 90px #000a}.settings.show{display:block}select{width:100%;background:#070d1c;color:#eef3ff;border:1px solid #344563;border-radius:14px;padding:12px;margin:8px 0 14px}@media(max-width:980px){.grid,.row,.quick{grid-template-columns:1fr}}
</style></head>
<body><div class="app"><div class="top"><div class="brand">magicStudio</div><div><span class="badge" id="state">준비됨</span> <button onclick="toggleSettings()">설정</button></div></div><section class="hero"><h1>한 줄로 제작하세요</h1><div class="sub">원고를 붙이고 원하는 결과를 말하면, 기획·장면·자막·TTS·프리뷰까지 자동으로 만듭니다.</div><div class="row"><input id="title" value="불법강호" placeholder="프로젝트명"><input id="idea" value="현대 서울에 깨어난 백 년 전 무인이 국가등록무림과 충돌하는 3분 시리즈" placeholder="아이디어 한 줄"></div><textarea id="prompt" class="prompt">현재 원고로 1분짜리 쇼츠 프리뷰를 만들어줘. 한국어 내레이션과 자막을 넣고, 바로 재생 가능한 mp4까지 만들어줘.</textarea><button class="make" onclick="makeAll()">전체 자동 제작</button><div class="quick"><button onclick="planOnly()">기획만 보기</button><button onclick="previewOnly()">프리뷰만 다시 만들기</button><button onclick="toggleAdvanced()">원고 열기</button></div><div id="advanced" class="advanced"><div class="small">원고를 수정한 뒤 다시 “전체 자동 제작”을 누르면 됩니다.</div><textarea id="scenario" class="script"></textarea></div></section><section class="grid"><div class="card"><div class="head">프리뷰</div><div class="body"><video id="video" controls></video><div class="small" id="previewText">아직 생성된 프리뷰가 없습니다.</div></div></div><div class="card"><div class="head">진행 상태</div><div class="body"><div id="steps" class="steps"></div></div></div></section><section class="grid"><div class="card"><div class="head">실행 로그</div><div class="body"><div id="log" class="log"></div></div></div><div class="card"><div class="head">상세</div><div class="body"><div id="detail" class="log"></div></div></div></section></div><div id="settings" class="settings"><h3>설정</h3><div class="small">기본값으로 충분합니다. 필요할 때만 바꾸세요.</div><label>TTS 음성</label><select id="voice"><option>Microsoft Heami Desktop</option><option>Microsoft Zira Desktop</option><option>Microsoft David Desktop</option></select><label>자막</label><select id="burn"><option value="true">영상에 직접 넣기</option><option value="false">자막 파일만 만들기</option></select><button onclick="toggleSettings()">닫기</button></div><script>
const DEFAULT_SCENARIO=`__SCENARIO__`; scenario.value=DEFAULT_SCENARIO; function logMsg(s){log.textContent+=(log.textContent?'\n':'')+'['+new Date().toLocaleTimeString()+'] '+s;log.scrollTop=log.scrollHeight} function toggleSettings(){settings.classList.toggle('show')} function toggleAdvanced(){advanced.classList.toggle('show')} async function api(p,d){const r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json; charset=utf-8'},body:JSON.stringify(d||{})});const j=await r.json();if(!j.ok)throw new Error(j.error||'실패');return j} async function getJson(p){const r=await fetch(p);return await r.json()} function data(){return{title:title.value.trim()||'불법강호',idea:idea.value.trim(),scenario:scenario.value,command:prompt.value,voice:voice.value,burn_subtitles:burn.value==='true'}} async function makeAll(){try{state.textContent='제작 중...';logMsg('전체 자동 제작 시작');const j=await api('/api/make',data());logMsg(j.message);await refresh();state.textContent='완료'}catch(e){state.textContent='오류';logMsg(e.message)}} async function planOnly(){try{state.textContent='기획 중...';const j=await api('/api/plan',data());logMsg(j.message);await refresh();state.textContent='기획 완료'}catch(e){logMsg(e.message)}} async function previewOnly(){try{state.textContent='렌더 중...';const j=await api('/api/preview',data());logMsg(j.message);await refresh();state.textContent='프리뷰 완료'}catch(e){logMsg(e.message)}} async function refresh(){const j=await getJson('/api/project?title='+encodeURIComponent(title.value.trim()||'불법강호'));if(j.scenario)scenario.value=j.scenario;if(j.preview_url){video.src=j.preview_url+'?t='+Date.now();previewText.textContent='프리뷰 준비 완료'}renderSteps(j);detail.textContent=JSON.stringify({asset:j.asset_manifest&&j.asset_manifest.summary,preview:j.preview_result},null,2)} function renderSteps(j){const s=(j.asset_manifest&&j.asset_manifest.summary)||{};const audio=(j.preview_result&&j.preview_result.audio)||{};const rows=[['기획',!!j.keyframe_prompts],['자막',!!j.preview_url],['음성',audio.used_real_audio_count>0],['프리뷰',!!j.preview_url],['누락 없음',s.total&&s.missing===0]];steps.innerHTML='';rows.forEach(r=>{const d=document.createElement('div');d.className='step';d.innerHTML='<span>'+r[0]+'</span><span class="dot '+(r[1]?'ok':'')+'"></span>';steps.appendChild(d)})} refresh().catch(()=>{});
</script></body></html>'''.replace('__SCENARIO__', DEFAULT_SCENARIO.replace('`','\\`'))

class Handler(BaseHTTPRequestHandler):
    workspace: Path = ROOT_DIR
    def send_json(self,payload:Any,status:int=200)->None:
        data=json.dumps(payload,ensure_ascii=False).encode('utf-8');self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def send_html(self)->None:
        data=HTML.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def body(self)->Dict[str,Any]:
        n=int(self.headers.get('Content-Length','0') or '0');return json.loads(self.rfile.read(n).decode('utf-8')) if n else {}
    def do_GET(self)->None:
        p=urlparse(self.path)
        try:
            if p.path=='/': self.send_html()
            elif p.path=='/api/project': self.send_json(load_project_payload(self.workspace,parse_qs(p.query).get('title',['불법강호'])[0]))
            elif p.path.startswith('/media/'): self.media(p.path)
            else: self.send_json({'ok':False,'error':'not found'},404)
        except Exception as e: self.send_json({'ok':False,'error':str(e)},500)
    def do_POST(self)->None:
        try:
            b=self.body();p=urlparse(self.path).path;title=str(b.get('title','불법강호')).strip() or '불법강호';idea=str(b.get('idea',DEFAULT_IDEA)).strip() or DEFAULT_IDEA;scenario=str(b.get('scenario',DEFAULT_SCENARIO)) or DEFAULT_SCENARIO
            if p=='/api/make': self.send_json({'ok':True,**self.make(title,idea,scenario,b)})
            elif p=='/api/plan': save_scenario(self.workspace,title,idea,scenario);run_pipeline(self.workspace,title,idea,scenario);self.send_json({'ok':True,'message':'기획 생성 완료'})
            elif p=='/api/preview': render_preview(self.workspace,title,bool(b.get('burn_subtitles',True)));inspect_assets(self.workspace,title);self.send_json({'ok':True,'message':'프리뷰 렌더 완료'})
            else: self.send_json({'ok':False,'error':'not found'},404)
        except Exception as e: self.send_json({'ok':False,'error':str(e)},500)
    def make(self,title:str,idea:str,scenario:str,b:Dict[str,Any])->Dict[str,Any]:
        save_scenario(self.workspace,title,idea,scenario);run_pipeline(self.workspace,title,idea,scenario);synth_tts(self.workspace,title,str(b.get('voice','Microsoft Heami Desktop')));render_preview(self.workspace,title,bool(b.get('burn_subtitles',True)));inspect_assets(self.workspace,title);return {'message':'전체 자동 제작 완료'}
    def media(self,path_text:str)->None:
        rel=path_text[len('/media/'):];path=(self.workspace/'local_projects'/rel).resolve();root=(self.workspace/'local_projects').resolve()
        if not str(path).startswith(str(root)) or not path.exists(): self.send_response(404);self.end_headers();return
        data=path.read_bytes();self.send_response(200);self.send_header('Content-Type','video/mp4');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def log_message(self,format:str,*args:Any)->None: return

def main()->int:
    parser=argparse.ArgumentParser(description='Run minimal prompt-first magicStudio UI');parser.add_argument('--workspace',default='.');parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',type=int,default=7863);args=parser.parse_args();Handler.workspace=Path(args.workspace).resolve();server=ThreadingHTTPServer((args.host,args.port),Handler);print('=== magicStudio Easy UI ===');print(f'workspace: {Handler.workspace}');print(f'url: http://{args.host}:{args.port}')
    try: server.serve_forever()
    except KeyboardInterrupt: print('\nshutdown')
    finally: server.server_close()
    return 0
if __name__=='__main__': raise SystemExit(main())
