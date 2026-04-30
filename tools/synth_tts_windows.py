from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
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


def powershell_executable() -> str:
    return "powershell.exe"


def list_voices() -> int:
    script = r'''
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
foreach ($voice in $synth.GetInstalledVoices()) {
  $info = $voice.VoiceInfo
  Write-Output ($info.Name + " | " + $info.Culture + " | " + $info.Gender + " | " + $info.Age)
}
$synth.Dispose()
'''
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = Path(temp_dir) / "list_voices.ps1"
        write_text(script_path, script)
        completed = subprocess.run(
            [powershell_executable(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        print(completed.stdout)
        if completed.stderr.strip():
            print(completed.stderr, file=sys.stderr)
        return completed.returncode


def synthesize_one(
    text: str,
    output_path: Path,
    voice: str,
    rate: int,
    volume: int,
) -> Dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        text_path = temp_root / "tts_text.txt"
        script_path = temp_root / "synth.ps1"
        write_text(text_path, text)
        escaped_voice = voice.replace("'", "''")
        escaped_text_path = str(text_path).replace("'", "''")
        escaped_output_path = str(output_path).replace("'", "''")
        script = f'''
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
$text = Get-Content -LiteralPath '{escaped_text_path}' -Raw -Encoding UTF8
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
if ('{escaped_voice}'.Length -gt 0) {{
  $synth.SelectVoice('{escaped_voice}')
}}
$synth.Rate = {rate}
$synth.Volume = {volume}
$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(48000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$synth.SetOutputToWaveFile('{escaped_output_path}', $format)
$synth.Speak($text)
$synth.Dispose()
'''
        write_text(script_path, script)
        completed = subprocess.run(
            [powershell_executable(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "ok": completed.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "output_path": str(output_path),
            "size_bytes": output_path.stat().st_size if output_path.exists() else 0,
        }


def synthesize_episode(
    episode_dir: Path,
    voice: str,
    rate: int,
    volume: int,
) -> Dict[str, Any]:
    tts_path = episode_dir / "tts_script.json"
    if not tts_path.exists():
        raise FileNotFoundError(f"tts_script.json not found: {tts_path}")

    payload = read_json(tts_path)
    audio_dir = episode_dir / "audio"
    results: List[Dict[str, Any]] = []
    ok_count = 0

    for cue in payload.get("cues", []):
        scene_id = str(cue.get("scene_id", "")).strip()
        text = str(cue.get("text", "")).strip()
        if not scene_id or not text:
            continue
        output_path = audio_dir / f"{scene_id}_narration.wav"
        result = synthesize_one(text=text, output_path=output_path, voice=voice, rate=rate, volume=volume)
        result["scene_id"] = scene_id
        result["scene_title"] = cue.get("scene_title", "")
        result["text"] = text
        results.append(result)
        if result["ok"]:
            ok_count += 1

    summary = {
        "ok": ok_count == len(results) and len(results) > 0,
        "episode_dir": str(episode_dir),
        "audio_dir": str(audio_dir),
        "voice": voice,
        "rate": rate,
        "volume": volume,
        "total": len(results),
        "ok_count": ok_count,
        "results": results,
    }
    report_path = audio_dir / "tts_synthesis_result.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate real narration WAV files from tts_script.json using Windows SAPI.")
    parser.add_argument("episode_dir", nargs="?", help="Episode folder containing tts_script.json")
    parser.add_argument("--voice", default="", help="Installed Windows SAPI voice name. Omit to use the Windows default voice.")
    parser.add_argument("--rate", type=int, default=0, help="Speech rate from -10 to 10. Default: 0")
    parser.add_argument("--volume", type=int, default=100, help="Speech volume from 0 to 100. Default: 100")
    parser.add_argument("--list-voices", action="store_true", help="List installed Windows SAPI voices and exit.")
    args = parser.parse_args()

    if args.list_voices:
        return list_voices()

    if not args.episode_dir:
        parser.error("episode_dir is required unless --list-voices is used")

    rate = max(-10, min(10, args.rate))
    volume = max(0, min(100, args.volume))
    summary = synthesize_episode(Path(args.episode_dir), voice=args.voice, rate=rate, volume=volume)

    print("=== magicStudio Windows TTS Synthesis ===")
    print(f"ok: {summary['ok']}")
    print(f"voice: {summary['voice'] or '(windows default)'}")
    print(f"audio_dir: {summary['audio_dir']}")
    print(f"ok_count: {summary['ok_count']} / {summary['total']}")
    for item in summary["results"]:
        status = "OK" if item["ok"] else "FAIL"
        print(f"{status}: {item['scene_id']} -> {item['output_path']} ({item['size_bytes']} bytes)")
        if not item["ok"] and item.get("stderr"):
            print(item["stderr"], file=sys.stderr)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
