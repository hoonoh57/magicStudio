from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def classify_assets(assets: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    missing: List[Dict[str, Any]] = []
    existing: List[Dict[str, Any]] = []
    placeholders: List[Dict[str, Any]] = []
    real_narration: List[Dict[str, Any]] = []
    preview_outputs: List[Dict[str, Any]] = []
    plan_files: List[Dict[str, Any]] = []

    for asset in assets:
        asset_type = str(asset.get("asset_type", ""))
        exists = bool(asset.get("exists", False))
        rel_path = str(asset.get("relative_path", ""))
        size_bytes = int(asset.get("size_bytes", 0))
        if exists:
            existing.append(asset)
        else:
            missing.append(asset)

        if asset_type == "keyframe_image" and exists:
            # In current MVP, generated keyframes are placeholder cards until replaced by real images.
            placeholders.append(asset)
        elif asset_type == "narration_audio" and exists and size_bytes > 0:
            real_narration.append(asset)
        elif asset_type == "preview_output":
            preview_outputs.append(asset)
        elif asset_type == "production_plan":
            plan_files.append(asset)

    return {
        "missing": missing,
        "existing": existing,
        "placeholders": placeholders,
        "real_narration": real_narration,
        "preview_outputs": preview_outputs,
        "plan_files": plan_files,
    }


def by_type_summary(assets: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    result: Dict[str, Dict[str, int]] = {}
    for asset in assets:
        asset_type = str(asset.get("asset_type", "unknown"))
        if asset_type not in result:
            result[asset_type] = {"total": 0, "existing": 0, "missing": 0}
        result[asset_type]["total"] += 1
        if asset.get("exists"):
            result[asset_type]["existing"] += 1
        else:
            result[asset_type]["missing"] += 1
    return result


def md_table(rows: List[List[str]], headers: List[str]) -> str:
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        safe_row = [str(cell).replace("\n", " ").replace("|", "\\|") for cell in row]
        lines.append("| " + " | ".join(safe_row) + " |")
    return "\n".join(lines)


def asset_rows(assets: List[Dict[str, Any]], limit: int = 30) -> List[List[str]]:
    rows: List[List[str]] = []
    for asset in assets[:limit]:
        rows.append([
            str(asset.get("asset_type", "")),
            str(asset.get("role", "")),
            str(asset.get("scene_title", "")),
            str(asset.get("relative_path", "")),
            "YES" if asset.get("exists") else "NO",
            str(asset.get("size_bytes", 0)),
        ])
    return rows


def recommend_actions(groups: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    actions: List[str] = []
    if groups["missing"]:
        actions.append("누락 자산을 먼저 보완하세요. 특히 narration_audio 또는 preview_output 누락은 최종 렌더 실패 원인이 됩니다.")
    if groups["placeholders"]:
        actions.append("placeholder keyframe 이미지를 실제 생성 이미지로 교체하세요. 파일명은 asset_manifest.json의 relative_path를 그대로 사용하면 자동 반영됩니다.")
    if not groups["real_narration"]:
        actions.append("실제 narration WAV가 없습니다. tools/synth_tts_windows.py 또는 외부 TTS provider로 audio/<scene_id>_narration.wav를 생성하세요.")
    if groups["real_narration"] and not groups["missing"]:
        actions.append("현재 자산 상태는 preview 제작 기준 통과입니다. 다음 단계는 실제 keyframe 이미지 교체와 음악/SFX provider 연결입니다.")
    return actions


def build_report(manifest_path: Path, manifest: Dict[str, Any]) -> str:
    assets = manifest.get("assets", [])
    summary = manifest.get("summary", {})
    groups = classify_assets(assets)
    type_summary = by_type_summary(assets)

    lines: List[str] = []
    lines.append("# magicStudio Asset Report")
    lines.append("")
    lines.append(f"- Manifest: `{manifest_path}`")
    lines.append(f"- Project: `{manifest.get('title', '')}`")
    lines.append(f"- Episode Dir: `{manifest.get('episode_dir', '')}`")
    lines.append(f"- Existing: **{summary.get('existing', 0)} / {summary.get('total', 0)}**")
    lines.append(f"- Missing: **{summary.get('missing', 0)}**")
    lines.append("")

    rows: List[List[str]] = []
    for asset_type, row in sorted(type_summary.items()):
        rows.append([asset_type, str(row["total"]), str(row["existing"]), str(row["missing"])])
    lines.append("## Summary by Type")
    lines.append("")
    lines.append(md_table(rows, ["asset_type", "total", "existing", "missing"]))
    lines.append("")

    lines.append("## Recommended Next Actions")
    lines.append("")
    for action in recommend_actions(groups):
        lines.append(f"- {action}")
    lines.append("")

    if groups["missing"]:
        lines.append("## Missing Assets")
        lines.append("")
        lines.append(md_table(asset_rows(groups["missing"], 50), ["type", "role", "scene", "path", "exists", "bytes"]))
        lines.append("")

    lines.append("## Placeholder Keyframes")
    lines.append("")
    if groups["placeholders"]:
        lines.append(md_table(asset_rows(groups["placeholders"], 50), ["type", "role", "scene", "path", "exists", "bytes"]))
    else:
        lines.append("No placeholder keyframe images found.")
    lines.append("")

    lines.append("## Narration Audio")
    lines.append("")
    if groups["real_narration"]:
        lines.append(md_table(asset_rows(groups["real_narration"], 50), ["type", "role", "scene", "path", "exists", "bytes"]))
    else:
        lines.append("No narration audio files found.")
    lines.append("")

    lines.append("## Preview Outputs")
    lines.append("")
    lines.append(md_table(asset_rows(groups["preview_outputs"], 50), ["type", "role", "scene", "path", "exists", "bytes"]))
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect asset_manifest.json and write asset_report.md.")
    parser.add_argument("episode_dir", help="Episode folder containing asset_manifest.json")
    args = parser.parse_args()

    episode_dir = Path(args.episode_dir)
    manifest_path = episode_dir / "asset_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"asset_manifest.json not found: {manifest_path}")

    manifest = read_json(manifest_path)
    report = build_report(manifest_path, manifest)
    report_path = episode_dir / "asset_report.md"
    write_text(report_path, report)

    summary = manifest.get("summary", {})
    groups = classify_assets(manifest.get("assets", []))

    print("=== magicStudio Asset Inspection ===")
    print(f"asset_manifest: {manifest_path}")
    print(f"asset_report: {report_path}")
    print(f"existing: {summary.get('existing', 0)} / {summary.get('total', 0)}")
    print(f"missing: {summary.get('missing', 0)}")
    print(f"placeholder_keyframes: {len(groups['placeholders'])}")
    print(f"narration_audio: {len(groups['real_narration'])}")
    print(f"preview_outputs: {len(groups['preview_outputs'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
