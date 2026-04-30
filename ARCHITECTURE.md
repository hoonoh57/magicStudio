# magicStudio Architecture

## 1. Product Definition

magicStudio는 장르에 구애받지 않고 입력된 소재를 시장성·제작성 기준으로 평가한 뒤, 통과한 소재를 프로젝트화하여 시나리오, 전역 제작 Bible, VML, 키프레임, 음성, 자막, 음악, 편집 타임라인까지 자동 생성하는 범용 1인 AI 제작 스튜디오다.

## 2. Core Philosophy

```text
기능은 버리지 않는다.
구현 우선순위와 실행 경로를 나눈다.
외부 API는 옵션이고, 내부 대체수단은 반드시 가진다.
```

## 3. Layered Execution Model

### Level A. Core Native Engine

magicStudio가 직접 가져야 하는 엔진:

- ProjectManager
- IdeaAnalyzer
- MarketEvaluator
- ProductionEvaluator
- BibleBuilder
- ScenarioManager
- SceneBreaker
- VmlEngine
- AssetManager
- TimelineBuilder
- ReviewManager
- FeedbackManager

### Level B. Built-in Basic Engine

외부 API 없이도 기본 제작이 가능해야 한다.

- 기본 이미지 프롬프트 생성
- 기본 TTS 스크립트 생성
- SRT/ASS 생성
- music_plan/sfx_plan 생성
- FFmpeg 렌더 스크립트 생성
- 키프레임 기반 슬라이드 영상 조립

### Level C. External Provider Plugin

전문 사용자가 선택 가능해야 한다.

- LLM: OpenAI, Claude, Gemini, local LLM
- Image: ComfyUI, SDXL, Flux
- Video: Runway, Pika, Kling, Luma, Sora 등
- TTS: ElevenLabs, OpenAI TTS, Azure, local TTS
- Music: Suno, Udio, local audio model, asset library
- Editor: Premiere, Resolve, Final Cut, CapCut, FlowCut
- Render: FFmpeg, MoviePy, Blender

## 4. Data Flow

```text
RawIdea
  ↓
IdeaAnalysis
  ↓
MarketEvaluation + ProductionEvaluation
  ↓
Project
  ↓
ProjectBible
  ↓
EpisodeScenario
  ↓
SceneBreakdown
  ↓
VML
  ↓
AssetsPlan
  ↓
Timeline
  ↓
ExportPackage
  ↓
ReviewReport
  ↓
Revision
```

## 5. Internal Standards

### VML

VML은 프롬프트가 아니라 제작 명령서다.

VML에서 파생되는 산출물:

- image prompt
- video prompt
- TTS script
- subtitle lines
- music cue
- sfx cue
- timeline clip
- review checklist

### timeline.json

모든 편집기 export의 내부 기준이다.

```text
timeline.json
→ Premiere XML
→ FCPXML
→ DaVinci Resolve XML
→ FlowCut project
→ FFmpeg render script
```

## 6. Project Folder Layout

```text
magicStudio/
│
├── CODING_BIBLE.md
├── ARCHITECTURE.md
├── TODO.md
├── SKILLS.md
├── PROJECT_RULES.json
├── EXECUTION_CONTRACT_SCHEMA.json
├── CHANGELOG.md
│
├── app/
│   ├── core/
│   ├── services/
│   ├── exporters/
│   ├── plugins/
│   ├── schemas/
│   └── ui/
│
├── genre_profiles/
├── provider_profiles/
├── project_templates/
├── tools/
├── tests/
└── projects/
```

## 7. Core Module Boundaries

- `ProjectManager`: 프로젝트 생성/상태/폴더 구조
- `IdeaAnalyzer`: 소재 구조화
- `MarketEvaluator`: 시장성 평가
- `ProductionEvaluator`: 1인 자동화 제작성 평가
- `BibleBuilder`: 전역 제작 Bible 생성
- `SceneBreaker`: 회차를 키신으로 분해
- `VmlEngine`: 키신을 VML로 변환
- `TimelineBuilder`: VML/에셋을 timeline.json으로 조립
- `Exporter`: 외부 형식 출력
- `ReviewManager`: 검수/반송
- `FeedbackManager`: 공개 후 성과 기록

## 8. Non-Negotiable Boundaries

```text
Provider는 core에 직접 들어오지 않는다.
UI는 core 로직을 직접 수정하지 않는다.
genre_profile은 코드가 아니라 데이터다.
프로젝트 Bible은 생성 프롬프트보다 우선한다.
사용자 locked asset은 자동 재생성하지 않는다.
```
