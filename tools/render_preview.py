from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.exporters.ffmpeg_preview_renderer import FfmpegPreviewRenderer


def main() -> int:
    parser = argparse.ArgumentParser(description="Render local preview mp4 from preview_render_plan.json.")
    parser.add_argument(
        "episode_dir",
        help="Episode folder containing preview_render_plan.json, e.g. local_projects/불법강호/episodes/ep001",
    )
    parser.add_argument("--ffmpeg", default="ffmpeg", help="Path to ffmpeg executable")
    args = parser.parse_args()

    renderer = FfmpegPreviewRenderer(ffmpeg_path=args.ffmpeg)
    result = renderer.render_from_file(Path(args.episode_dir))

    print("=== magicStudio Preview Render ===")
    print(f"ok: {result['ok']}")
    print(f"mode: {result['mode']}")
    print(f"output_path: {result['output_path']}")
    print(f"captions_sidecar: {result['captions_sidecar']}")
    print(f"scene_manifest: {result['scene_manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
