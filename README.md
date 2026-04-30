# magicStudio

magicStudio는 특정 장르 전용 제작기가 아니라, 어떤 소재든 입력하면 시장성·제작성·자동화 적합성을 평가하고, 통과한 소재를 프로젝트화하여 시나리오, 전역 제작 Bible, VML, 키프레임, TTS, 자막, 음악, 편집 타임라인까지 생성하는 범용 1인 AI 제작 스튜디오입니다.

## Product Identity

- 작가는 작품을 만든다.
- magicStudio는 작품을 제작 가능한 프로젝트 데이터로 변환한다.
- 핵심 표준은 `Project Bible`, `VML`, `timeline.json`이다.
- 외부 API는 옵션이며, 내부 기본 경로와 수동 등록 경로를 항상 둔다.

## Initial Goal

MVP 0.1의 목표는 영상 생성기가 아니라 제작 설계 자동화입니다.

```text
소재 입력
→ 시장성/제작성 평가
→ 프로젝트 생성
→ Project Bible 생성
→ 회차 등록
→ 키신 분해
→ VML 생성
→ 키프레임 프롬프트/TTS/SRT/music_plan/timeline.json 출력
```

## Core Documents

- `CODING_BIBLE.md`: 개발 헌법
- `ARCHITECTURE.md`: 제품/엔진 구조
- `TODO.md`: 단계별 구현 계획
- `PROJECT_RULES.json`: 자동화/코드 생성 규칙
- `EXECUTION_CONTRACT_SCHEMA.json`: 작업 계약 스키마
- `SKILLS.md`: 참조 스킬/룰 목록
- `CHANGELOG.md`: 변경 기록
