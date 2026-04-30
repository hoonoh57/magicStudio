const App = {
  title: '',
  currentTab: 'project',
  project: null,
};

function qs(id) {
  return document.getElementById(id);
}

function log(message) {
  const box = qs('logBox');
  const prefix = new Date().toLocaleTimeString();
  box.textContent += (box.textContent ? '\n' : '') + `[${prefix}] ${message}`;
  box.scrollTop = box.scrollHeight;
}

function setServerState(text) {
  qs('serverState').textContent = text;
}

async function getJson(url) {
  const response = await fetch(url, { method: 'GET' });
  const text = await response.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch (error) {
    throw new Error(`JSON 파싱 실패: ${text.slice(0, 200)}`);
  }
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify(payload || {}),
  });
  const text = await response.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch (error) {
    throw new Error(`JSON 파싱 실패: ${text.slice(0, 200)}`);
  }
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

function payload() {
  return {
    title: qs('projectTitle').value.trim() || '불법강호',
    idea: qs('projectIdea').value.trim(),
    scenario: qs('scenarioText').value,
    command: qs('masterCommand').value,
    voice: qs('voiceSelect').value,
    burn_subtitles: qs('subtitleMode').value === 'true',
  };
}

function switchTab(tabName) {
  App.currentTab = tabName;
  document.querySelectorAll('.tab').forEach((node) => {
    node.classList.toggle('active', node.dataset.tab === tabName);
  });
  document.querySelectorAll('.stage').forEach((node) => {
    node.classList.toggle('active', node.id === `stage-${tabName}`);
  });
}

function renderProjects(projects) {
  const box = qs('projectList');
  box.innerHTML = '';
  if (!projects || projects.length === 0) {
    box.innerHTML = '<div class="muted">아직 저장된 프로젝트가 없습니다.</div>';
    return;
  }
  projects.forEach((project) => {
    const item = document.createElement('div');
    item.className = 'project-item' + (project.title === qs('projectTitle').value ? ' active' : '');
    item.innerHTML = `<b>${escapeHtml(project.title)}</b><div class="muted">${escapeHtml(project.status || '')}</div><div class="muted">${escapeHtml(project.path || '')}</div>`;
    item.addEventListener('click', async () => {
      qs('projectTitle').value = project.title;
      await loadProject();
      await loadProjects();
      switchTab('scenario');
    });
    box.appendChild(item);
  });
}

function renderStatus(project) {
  const box = qs('statusList');
  const summary = project?.asset_manifest?.summary || {};
  const preview = project?.preview_result || {};
  const audio = preview.audio || {};
  const rows = [
    ['프로젝트', Boolean(project?.exists)],
    ['시나리오', Boolean(project?.scenario)],
    ['프롬프트', Boolean(project?.keyframe_prompts)],
    ['TTS 음성', Number(audio.used_real_audio_count || 0) > 0],
    ['MP4 프리뷰', Boolean(project?.preview_url)],
    ['자산 누락 없음', Boolean(summary.total && summary.missing === 0)],
  ];
  box.innerHTML = '';
  rows.forEach(([name, ok]) => {
    const row = document.createElement('div');
    row.className = 'status-row';
    row.innerHTML = `<span>${name}</span><span class="dot ${ok ? 'ok' : ''}"></span>`;
    box.appendChild(row);
  });
}

function renderPrompts(project) {
  const box = qs('promptList');
  box.innerHTML = '';
  const prompts = project?.keyframe_prompts?.prompts || [];
  if (prompts.length === 0) {
    box.innerHTML = '<div class="muted">아직 프롬프트가 없습니다. 먼저 “장면/프롬프트 생성”을 누르세요.</div>';
    return;
  }
  prompts.forEach((prompt, index) => {
    const card = document.createElement('div');
    card.className = 'prompt-card';
    card.innerHTML = `<b>${index + 1}. ${escapeHtml(prompt.scene_title || '장면')}</b><div class="muted">${escapeHtml(prompt.keyframe_id || '')}</div><div>${escapeHtml(prompt.prompt || '')}</div>`;
    box.appendChild(card);
  });
}

function renderPreview(project) {
  const video = qs('previewVideo');
  if (project?.preview_url) {
    video.src = `${project.preview_url}?t=${Date.now()}`;
  }
  qs('previewResult').textContent = project?.preview_result ? JSON.stringify(project.preview_result, null, 2) : '';
}

function renderProject(project) {
  App.project = project;
  qs('projectTitle').value = project.title || qs('projectTitle').value;
  qs('projectIdea').value = project.idea || qs('projectIdea').value;
  qs('scenarioText').value = project.scenario || '';
  qs('projectPathBox').textContent = project.project_root ? `프로젝트 경로: ${project.project_root}\n원고 경로: ${project.scenario_path}` : '저장 경로가 여기에 표시됩니다.';
  renderStatus(project);
  renderPrompts(project);
  renderPreview(project);
  if (project.asset_report) {
    qs('assetReport').textContent = project.asset_report;
  }
}

async function loadDefaults() {
  const data = await getJson('/api/defaults');
  qs('projectTitle').value = data.title;
  qs('projectIdea').value = data.idea;
  qs('scenarioText').value = data.scenario;
  qs('masterCommand').value = '이 원고로 1분짜리 쇼츠 프리뷰를 만들고, 한국어 TTS와 자막을 넣어줘.';
}

async function ping() {
  const data = await getJson('/api/ping');
  setServerState(`서버 OK: ${data.workspace}`);
}

async function loadProjects() {
  const data = await getJson('/api/projects');
  renderProjects(data.projects || []);
  log(`프로젝트 목록 로드: ${(data.projects || []).length}개`);
}

async function saveProject() {
  const data = await postJson('/api/project/save', payload());
  log(`저장 완료: ${data.scenario_path}`);
  await loadProjects();
  await loadProject();
}

async function loadProject() {
  const data = await getJson(`/api/project?title=${encodeURIComponent(qs('projectTitle').value.trim() || '불법강호')}`);
  renderProject(data);
  log(`불러오기 완료: ${data.title}`);
}

async function buildScenes() {
  const data = await postJson('/api/scenario/build', payload());
  log(`장면/프롬프트 생성 완료: scene_count=${data.scene_count}`);
  await loadProject();
  switchTab('prompt');
}

async function synthTts() {
  const data = await postJson('/api/tts/synth', payload());
  log(`TTS 생성 완료: ${data.ok_count || 0}/${data.total || 0}`);
  qs('mediaResult').textContent = JSON.stringify(data, null, 2);
  await loadProject();
}

async function renderVideo() {
  const data = await postJson('/api/preview/render', payload());
  log(`프리뷰 렌더 완료: ${data.mode || ''}`);
  qs('previewResult').textContent = JSON.stringify(data, null, 2);
  await loadProject();
  switchTab('video');
}

async function inspectAssets() {
  const data = await postJson('/api/assets/inspect', payload());
  log(`검수 완료: missing=${data.missing}`);
  qs('assetReport').textContent = data.report || '';
  await loadProject();
  switchTab('inspect');
}

async function makeAll() {
  const data = await postJson('/api/make/all', payload());
  log('전체 자동 제작 완료');
  qs('previewResult').textContent = JSON.stringify(data.preview || {}, null, 2);
  qs('assetReport').textContent = data.inspection?.report || '';
  await loadProject();
  await loadProjects();
  switchTab('video');
}

function escapeHtml(value) {
  return String(value || '').replace(/[&<>]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[char]));
}

function bindEvents() {
  document.querySelectorAll('.tab').forEach((node) => node.addEventListener('click', () => switchTab(node.dataset.tab)));
  qs('btnSettings').addEventListener('click', () => qs('settingsDialog').showModal());
  qs('btnCloseSettings').addEventListener('click', () => qs('settingsDialog').close());
  qs('btnRefresh').addEventListener('click', async () => safeRun(loadProjects));
  qs('btnSave').addEventListener('click', async () => safeRun(saveProject));
  qs('btnLoad').addEventListener('click', async () => safeRun(loadProject));
  qs('btnMakeAll').addEventListener('click', async () => safeRun(makeAll));
  qs('btnBuildScenes').addEventListener('click', async () => safeRun(buildScenes));
  qs('btnTts').addEventListener('click', async () => safeRun(synthTts));
  qs('btnInspectMedia').addEventListener('click', async () => safeRun(inspectAssets));
  qs('btnRender').addEventListener('click', async () => safeRun(renderVideo));
  qs('btnInspect').addEventListener('click', async () => safeRun(inspectAssets));
}

async function safeRun(fn) {
  try {
    await fn();
  } catch (error) {
    log(`오류: ${error.message}`);
    setServerState('오류 발생');
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  bindEvents();
  log('화면 준비 완료');
  await safeRun(loadDefaults);
  await safeRun(ping);
  await safeRun(loadProjects);
});
