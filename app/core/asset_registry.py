from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.core.models import write_json_file


class AssetRegistry:
    """Track local-only production assets used by an episode.

    The registry is deterministic and file-based. It does not upload or copy
    private media assets. It only records what is expected, what exists, and what
    was generated locally.
    """

    def build(
        self,
        episode_dir: Path | str,
        vml_episode: Dict[str, Any],
        preview_render_plan: Dict[str, Any] | None = None,
        tts_script: Dict[str, Any] | None = None,
        render_result: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        root = Path(episode_dir)
        assets: List[Dict[str, Any]] = []
        assets.extend(self._image_assets(root, preview_render_plan or {}))
        assets.extend(self._tts_assets(root, preview_render_plan or {}, tts_script or {}))
        assets.extend(self._plan_assets(root))
        assets.extend(self._preview_assets(root, render_result or {}))

        summary = self._summary(assets)
        return {
            "version": "0.1",
            "project_id": vml_episode.get("project_id", ""),
            "title": vml_episode.get("title", ""),
            "episode_dir": str(root),
            "local_only": True,
            "summary": summary,
            "assets": assets,
            "policy": [
                "Do not commit generated media assets to git.",
                "Keep user scenarios, renders, audio, keyframes, motions, and exports local.",
                "Only templates, source code, schemas, and safe configuration should be tracked.",
            ],
        }

    def build_and_save(
        self,
        episode_dir: Path | str,
        vml_episode: Dict[str, Any],
        preview_render_plan: Dict[str, Any] | None = None,
        tts_script: Dict[str, Any] | None = None,
        render_result: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        root = Path(episode_dir)
        payload = self.build(root, vml_episode, preview_render_plan, tts_script, render_result)
        write_json_file(root / "asset_manifest.json", payload)
        return payload

    def _image_assets(self, root: Path, preview_render_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for scene in preview_render_plan.get("scenes", []):
            scene_id = str(scene.get("scene_id", ""))
            scene_title = str(scene.get("title", ""))
            for slot in scene.get("image_slots", []):
                rel_path = str(slot.get("expected_image", ""))
                path = root / rel_path
                result.append(
                    self._asset_row(
                        asset_id=str(slot.get("slot_id", "")),
                        asset_type="keyframe_image",
                        role=str(slot.get("keyframe_id", "keyframe")),
                        scene_id=scene_id,
                        scene_title=scene_title,
                        relative_path=rel_path,
                        path=path,
                        metadata={
                            "shot_type": slot.get("shot_type", ""),
                            "visual_focus": slot.get("visual_focus", ""),
                            "prompt_ref": slot.get("prompt_ref", ""),
                        },
                    )
                )
        return result

    def _tts_assets(self, root: Path, preview_render_plan: Dict[str, Any], tts_script: Dict[str, Any]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        cue_map: Dict[str, Dict[str, Any]] = {}
        for cue in tts_script.get("cues", []):
            cue_map[str(cue.get("scene_id", ""))] = cue

        for scene in preview_render_plan.get("scenes", []):
            scene_id = str(scene.get("scene_id", ""))
            scene_title = str(scene.get("title", ""))
            rel_path = str(scene.get("narration", {}).get("expected_audio", ""))
            if not rel_path:
                rel_path = f"audio/{scene_id}_narration.wav"
            path = root / rel_path
            cue = cue_map.get(scene_id, {})
            result.append(
                self._asset_row(
                    asset_id=f"{scene_id}_narration",
                    asset_type="narration_audio",
                    role="narration",
                    scene_id=scene_id,
                    scene_title=scene_title,
                    relative_path=rel_path,
                    path=path,
                    metadata={
                        "speaker": cue.get("speaker", "narrator"),
                        "tts_ref": cue.get("tts_ref", "narration"),
                        "emotion": cue.get("emotion", ""),
                        "text": cue.get("text", scene.get("narration", {}).get("text", "")),
                    },
                )
            )
        return result

    def _plan_assets(self, root: Path) -> List[Dict[str, Any]]:
        names = [
            "scene_breakdown.json",
            "vml_scenes.json",
            "timeline.json",
            "captions.srt",
            "keyframe_prompts.json",
            "tts_script.json",
            "music_plan.json",
            "sfx_plan.json",
            "preview_render_plan.json",
            "export_package.json",
        ]
        result: List[Dict[str, Any]] = []
        for name in names:
            result.append(
                self._asset_row(
                    asset_id=name,
                    asset_type="production_plan",
                    role="plan_file",
                    scene_id="",
                    scene_title="",
                    relative_path=name,
                    path=root / name,
                    metadata={},
                )
            )
        return result

    def _preview_assets(self, root: Path, render_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        candidates = [
            "preview/preview.mp4",
            "preview/preview.srt",
            "preview/preview_audio.wav",
            "preview/preview_render_result.json",
            "preview/preview_scene_manifest.json",
            "preview/preview_image_concat.txt",
        ]
        for rel_path in candidates:
            result.append(
                self._asset_row(
                    asset_id=rel_path,
                    asset_type="preview_output",
                    role="preview",
                    scene_id="",
                    scene_title="",
                    relative_path=rel_path,
                    path=root / rel_path,
                    metadata={},
                )
            )
        if render_result:
            audio = render_result.get("audio", {})
            audio_path = str(audio.get("audio_path", ""))
            if audio_path:
                result.append(
                    self._asset_row(
                        asset_id="render_result_audio_path",
                        asset_type="preview_audio_mix",
                        role="render_audio_mix",
                        scene_id="",
                        scene_title="",
                        relative_path=self._relative_or_raw(root, Path(audio_path)),
                        path=Path(audio_path),
                        metadata={
                            "used_real_audio_count": audio.get("used_real_audio_count", 0),
                            "generated_silence_count": audio.get("generated_silence_count", 0),
                        },
                    )
                )
        return result

    def _asset_row(
        self,
        asset_id: str,
        asset_type: str,
        role: str,
        scene_id: str,
        scene_title: str,
        relative_path: str,
        path: Path,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        exists = path.exists()
        return {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "role": role,
            "scene_id": scene_id,
            "scene_title": scene_title,
            "relative_path": relative_path.replace("\\", "/"),
            "exists": exists,
            "size_bytes": path.stat().st_size if exists and path.is_file() else 0,
            "metadata": metadata,
        }

    def _summary(self, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(assets)
        existing = 0
        missing = 0
        by_type: Dict[str, Dict[str, int]] = {}
        for asset in assets:
            asset_type = str(asset.get("asset_type", "unknown"))
            if asset_type not in by_type:
                by_type[asset_type] = {"total": 0, "existing": 0, "missing": 0}
            by_type[asset_type]["total"] += 1
            if asset.get("exists"):
                existing += 1
                by_type[asset_type]["existing"] += 1
            else:
                missing += 1
                by_type[asset_type]["missing"] += 1
        return {
            "total": total,
            "existing": existing,
            "missing": missing,
            "by_type": by_type,
        }

    def _relative_or_raw(self, root: Path, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")
