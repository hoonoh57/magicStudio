from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.asset_registry import AssetRegistry
from app.exporters.ffmpeg_preview_renderer import FfmpegPreviewRenderer


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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

    episode_dir = Path(args.episode_dir)
    renderer = FfmpegPreviewRenderer(
        ffmpeg_path=args.ffmpeg,
        generate_placeholders=not args.no_placeholders,
        burn_subtitles=args.burn_subtitles,
    )
    result = renderer.render_from_file(episode_dir)

    vml_path = episode_dir / "vml_scenes.json"
    preview_plan_path = episode_dir / "preview_render_plan.json"
    tts_path = episode_dir / "tts_script.json"
    asset_manifest_path = episode_dir / "asset_manifest.json"
    asset_manifest = None
    if vml_path.exists() and preview_plan_path.exists() and tts_path.exists():
        asset_manifest = AssetRegistry().build_and_save(
            episode_dir=episode_dir,
            vml_episode=read_json(vml_path),
            preview_render_plan=read_json(preview_plan_path),
            tts_script=read_json(tts_path),
            render_result=result,
        )

    print("=== magicStudio Preview Render ===")
    print(f"ok: {result['ok']}")
    print(f"mode: {result['mode']}")
    print(f"burn_subtitles: {result.get('burn_subtitles', False)}")
    print(f"used_image_count: {result.get('used_image_count', 0)}")
    print(f"generated_placeholder_count: {result.get('generated_placeholder_count', 0)}")
    audio = result.get("audio", {})
    if isinstance(audio, dict):
        print(f"used_real_audio_count: {audio.get('used_real_audio_count', 0)}")
        print(f"generated_silence_count: {audio.get('generated_silence_count', 0)}")
    print(f"output_path: {result['output_path']}")
    print(f"captions_sidecar: {result['captions_sidecar']}")
    print(f"scene_manifest: {result['scene_manifest']}")
    if asset_manifest is not None:
        print(f"asset_manifest: {asset_manifest_path}")
        print(f"asset_existing: {asset_manifest['summary']['existing']} / {asset_manifest['summary']['total']}")
        print(f"asset_missing: {asset_manifest['summary']['missing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
