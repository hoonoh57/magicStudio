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
    parser.add_argument(
        "--burn-subtitles",
        action="store_true",
        help="Burn captions.srt directly into preview.mp4 while still keeping the sidecar SRT.",
    )
    parser.add_argument(
        "--no-placeholders",
        action="store_true",
        help="Disable automatic placeholder keyframe image generation.",
    )
    args = parser.parse_args()

    renderer = FfmpegPreviewRenderer(
        ffmpeg_path=args.ffmpeg,
        generate_placeholders=not args.no_placeholders,
        burn_subtitles=args.burn_subtitles,
    )
    result = renderer.render_from_file(Path(args.episode_dir))

    print("=== magicStudio Preview Render ===")
    print(f"ok: {result['ok']}")
    print(f"mode: {result['mode']}")
    print(f"burn_subtitles: {result.get('burn_subtitles', False)}")
    print(f"used_image_count: {result.get('used_image_count', 0)}")
    print(f"generated_placeholder_count: {result.get('generated_placeholder_count', 0)}")
    print(f"output_path: {result['output_path']}")
    print(f"captions_sidecar: {result['captions_sidecar']}")
    print(f"scene_manifest: {result['scene_manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
