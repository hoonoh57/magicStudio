from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


def format_srt_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    hours = total_ms // 3_600_000
    total_ms %= 3_600_000
    minutes = total_ms // 60_000
    total_ms %= 60_000
    secs = total_ms // 1000
    millis = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class SrtExporter:
    """Export subtitles from internal timeline.json payload."""

    def export_text(self, timeline: Dict[str, Any]) -> str:
        subtitle_track = self._find_subtitle_track(timeline)
        lines: List[str] = []
        index = 1
        for clip in subtitle_track.get("clips", []):
            text = str(clip.get("text", "")).strip()
            if not text:
                continue
            start = float(clip.get("start_sec", 0.0))
            end = float(clip.get("end_sec", start + 1.0))
            lines.append(str(index))
            lines.append(f"{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}")
            lines.append(text)
            lines.append("")
            index += 1
        return "\n".join(lines).rstrip() + "\n"

    def export_file(self, timeline: Dict[str, Any], output_path: Path | str) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.export_text(timeline), encoding="utf-8")
        return path

    def _find_subtitle_track(self, timeline: Dict[str, Any]) -> Dict[str, Any]:
        for track in timeline.get("tracks", []):
            if track.get("type") == "subtitle":
                return track
        return {"clips": []}
