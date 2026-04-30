from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import uuid


UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime(UTC_FORMAT)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Decision(str, Enum):
    MAKE_NOW = "MAKE_NOW"
    MAKE_PILOT = "MAKE_PILOT"
    REVISE = "REVISE"
    HOLD = "HOLD"
    REJECT = "REJECT"


class ProjectStatus(str, Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    IN_PRODUCTION = "IN_PRODUCTION"
    REVIEW = "REVIEW"
    ARCHIVED = "ARCHIVED"


@dataclass
class IdeaAnalysis:
    idea_id: str
    raw_text: str
    detected_genres: List[str]
    target_audience: List[str]
    format_candidates: List[str]
    core_hook: str
    risk_flags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


@dataclass
class EvaluationResult:
    score: float
    decision: Decision
    reasons: List[str]
    details: Dict[str, float] = field(default_factory=dict)

    def to_json(self) -> str:
        data = asdict(self)
        data["decision"] = self.decision.value
        return json.dumps(data, ensure_ascii=False, indent=2)


@dataclass
class Project:
    project_id: str
    title: str
    genre: str
    target_format: str
    root_path: str
    market_score: float = 0.0
    production_score: float = 0.0
    status: ProjectStatus = ProjectStatus.DRAFT
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class Episode:
    episode_id: str
    project_id: str
    episode_no: int
    title: str
    scenario_text: str
    status: str = "DRAFT"
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass
class Scene:
    scene_id: str
    episode_id: str
    scene_no: int
    title: str
    dramatic_function: str
    duration_sec: float
    source_text: str = ""
    vml_json: str = "{}"
    status: str = "DRAFT"


def safe_slug(text: str, fallback: str = "project") -> str:
    cleaned = []
    for ch in text.strip().lower():
        if ch.isalnum():
            cleaned.append(ch)
        elif ch in (" ", "-", "_", "."):
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or fallback


def write_json_file(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json_file(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
