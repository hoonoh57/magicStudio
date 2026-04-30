# magicStudio Coding Bible

이 문서는 magicStudio 개발의 최상위 규칙이다. 모든 코드 생성, 수정, 리팩터링, 문서 변경은 이 문서를 기준으로 한다.

## 1. 최상위 원칙

```text
작품은 작가에게 맡긴다.
시스템은 제작 공정을 맡는다.

창작은 자유롭게 둔다.
제작은 데이터화한다.

프롬프트를 저장하지 않는다.
프롬프트를 만들 수 있는 구조를 저장한다.

장르는 플러그인으로 둔다.
엔진은 장르 독립적으로 만든다.

영상 생성기는 교체 가능하게 둔다.
VML과 timeline.json은 내부 표준으로 고정한다.

AI가 만든 것은 검수한다.
사용자가 고친 것은 보호한다.

완벽한 자동화를 먼저 노리지 않는다.
반복 가능한 제작 루프를 먼저 만든다.
```

## 2. 계약 기반 개발 규칙

코드 수정은 반드시 실행 계약을 먼저 가진다.

필수 항목:

- `task_id`
- `goal`
- `allowed_files`
- `forbidden_files`
- `steps`
- `success_criteria`
- `verification_commands`
- `rollback_policy`
- `failure_report_schema`

계약에 없는 파일은 수정하지 않는다.

## 3. 금지 사항

```text
TODO.md 없이 신규 기능 착수 금지
allowed_files 밖 수정 금지
실패 후 임의 재수정 금지
대형 파일 전체 재작성 금지
인코딩 지정 없는 PowerShell 파일 쓰기 금지
findstr 결과를 기반으로 무작정 전체 치환 금지
Provider 코드를 core 엔진에 직접 하드코딩 금지
사용자 locked 파일 덮어쓰기 금지
검증 없이 성공 보고 금지
```

## 4. 파일 수정 규칙

수정 우선순위:

1. 새 파일 생성
2. 작은 함수 추가
3. 명확한 앵커 사이 replace block
4. 특정 함수 전체 교체
5. 파일 전체 재작성은 최후 수단

파일 전체 재작성 허용 조건:

- 초기 생성 파일
- 100라인 이하
- 사용자 수정 없음
- 계약의 `allowed_files`에 명시됨

## 5. 파일 크기 규칙

```text
Python 파일: 400~600라인 이하 권장
1000라인 초과 시 분리 검토
UI는 화면별 파일
core 엔진은 기능별 파일
Provider는 plugins 하위 분리
schema는 schemas 하위 분리
```

## 6. UTF-8 / Windows 규칙

모든 텍스트 파일은 UTF-8로 저장한다.

PowerShell 수정 시:

```powershell
Get-Content -Raw -Encoding UTF8
Set-Content -Encoding UTF8
```

권장 방식은 Python patch script다.

한글 포함 파일은 수정 전 `.bak` 백업을 만든다.

## 7. Provider 설계 규칙

외부 도구는 core에 직접 결합하지 않는다.

```text
Core Native Engine
Built-in Basic Engine
External Provider Plugin
Manual Asset Registration
```

네 경로를 모두 고려한다.

## 8. 내부 표준

- 장면 표준: `VML`
- 편집 표준: `timeline.json`
- 자막 표준: `SRT`, `ASS`
- 프로젝트 설정 표준: `project.json`
- 전역 제작 설정 표준: `project_bible.json`

## 9. 검증 규칙

작업마다 최소 하나 이상의 검증 명령이 있어야 한다.

권장 검증:

```bash
python -m py_compile app/core/*.py
pytest
python tools/check_utf8.py .
python tools/validate_json.py
python tools/validate_export_package.py projects/sample/exports/ep001
git status --short
git diff --stat
```

## 10. 실패 처리

실패하면 즉시 재코딩하지 않는다.

반드시 failure report를 작성한다.

필수 항목:

- stdout
- stderr
- exit_code
- changed_files
- git_status_short
- git_diff_stat
- rollback_done
- rollback_target_commit
- failure_class
- repro_command
