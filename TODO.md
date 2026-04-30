# TODO

## Phase 0. Project Safety / Foundation

- [ ] Initialize repository with documentation-first structure
- [ ] Add `CODING_BIBLE.md`
- [ ] Add `ARCHITECTURE.md`
- [ ] Add `PROJECT_RULES.json`
- [ ] Add `EXECUTION_CONTRACT_SCHEMA.json`
- [ ] Add `SKILLS.md`
- [ ] Add `CHANGELOG.md`
- [ ] Add `.gitignore`
- [ ] Add initial clean commit

## Phase 1. Core Skeleton

- [ ] Create `app/core/models.py`
- [ ] Create `app/core/db.py`
- [ ] Create `app/core/project_manager.py`
- [ ] Create `app/core/idea_analyzer.py`
- [ ] Create `app/core/market_evaluator.py`
- [ ] Create `app/core/production_evaluator.py`
- [ ] Create `tests/test_project_manager.py`

## Phase 2. Project Bible / Genre Profiles

- [ ] Create `app/core/bible_builder.py`
- [ ] Create `genre_profiles/wuxia.json`
- [ ] Create `genre_profiles/romance.json`
- [ ] Create `genre_profiles/horror.json`
- [ ] Create `genre_profiles/education.json`
- [ ] Create `genre_profiles/documentary.json`
- [ ] Create `schemas/project_bible.schema.json`

## Phase 3. Scenario → Key Scene → VML

- [ ] Create `app/core/scenario_manager.py`
- [ ] Create `app/core/scene_breaker.py`
- [ ] Create `app/core/vml_engine.py`
- [ ] Create `schemas/vml.schema.json`
- [ ] Create sample VML for one episode

## Phase 4. Asset / Timeline / Export

- [ ] Create `app/core/asset_manager.py`
- [ ] Create `app/core/timeline_builder.py`
- [ ] Create `app/exporters/srt_exporter.py`
- [ ] Create `app/exporters/ass_exporter.py`
- [ ] Create `app/exporters/timeline_json_exporter.py`
- [ ] Create `app/exporters/project_folder_exporter.py`
- [ ] Create `schemas/timeline.schema.json`

## Phase 5. Review / Revision Loop

- [ ] Create `app/core/review_manager.py`
- [ ] Create `app/core/feedback_manager.py`
- [ ] Create `schemas/review_report.schema.json`
- [ ] Add failure report generation
- [ ] Add locked asset protection

## Phase 6. Provider Interface

- [ ] Create `app/plugins/base.py`
- [ ] Create `ITextModelProvider`
- [ ] Create `IImageGenerationProvider`
- [ ] Create `IVideoGenerationProvider`
- [ ] Create `ITtsProvider`
- [ ] Create `IMusicProvider`
- [ ] Create local/manual provider stubs

## Phase 7. MVP UI

- [ ] Create simple project list UI
- [ ] Create idea input/evaluation panel
- [ ] Create project Bible viewer/editor
- [ ] Create episode scenario editor
- [ ] Create scene/VML viewer
- [ ] Create export package button

## MVP 0.1 Success Criteria

- [ ] Input one idea
- [ ] Generate market/production evaluation
- [ ] Create project folder
- [ ] Generate project Bible
- [ ] Register one episode
- [ ] Break episode into key scenes
- [ ] Generate VML
- [ ] Generate keyframe prompts
- [ ] Generate TTS script
- [ ] Generate SRT
- [ ] Generate music_plan.json
- [ ] Generate timeline.json
