# magicStudio Skills and Rules

magicStudio development must load and follow project-level rules before generating or modifying code.

## Required Skill Categories

### Contract / Execution

- `common-project-contract-rules`
- `large-llm-common-planner-rules`
- `large-llm-openai-gpt-planner`
- `execution-contract-first-development`
- `failure-report-and-rollback-rules`

### Python / Project

- `python-project-basics`
- `sqlite-schema-rules`
- `json-schema-validation-rules`
- `utf8-windows-powershell-rules`
- `small-module-refactor-rules`

### magicStudio Domain

- `magicstudio-project-rules`
- `project-bible-rules`
- `vml-scene-language-rules`
- `timeline-json-rules`
- `provider-plugin-rules`
- `asset-locking-rules`
- `review-revision-loop-rules`

## Required Development Ritual

```text
1. Read CODING_BIBLE.md
2. Read ARCHITECTURE.md
3. Check TODO.md
4. Create execution_contract
5. Confirm allowed_files
6. Modify files
7. Run verification
8. Produce success report or failure_report
9. Commit only after clean verification
```

## Rule Priority

1. User explicit instruction
2. CODING_BIBLE.md
3. PROJECT_RULES.json
4. EXECUTION_CONTRACT_SCHEMA.json
5. ARCHITECTURE.md
6. TODO.md
7. Module-specific docstring
