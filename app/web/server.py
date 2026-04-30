from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, unquote, urlparse

from app.web import services


WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"


class MagicStudioHandler(BaseHTTPRequestHandler):
    workspace: Path = Path.cwd()

    def _json(self, payload: Any, status_code: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=None).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> Dict[str, Any]:
        size = int(self.headers.get("Content-Length", "0") or "0")
        if size <= 0:
            return {}
        raw = self.rfile.read(size).decode("utf-8")
        return json.loads(raw) if raw else {}

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path in ("/", "/index.html"):
                self._file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            elif parsed.path == "/app.js":
                self._file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
            elif parsed.path == "/style.css":
                self._file(STATIC_DIR / "style.css", "text/css; charset=utf-8")
            elif parsed.path == "/api/ping":
                self._json({"ok": True, "workspace": str(self.workspace)})
            elif parsed.path == "/api/defaults":
                self._json({"ok": True, "title": services.DEFAULT_TITLE, "idea": services.DEFAULT_IDEA, "scenario": services.DEFAULT_SCENARIO})
            elif parsed.path == "/api/projects":
                self._json({"ok": True, "projects": services.list_projects(self.workspace)})
            elif parsed.path == "/api/project":
                title = parse_qs(parsed.query).get("title", [services.DEFAULT_TITLE])[0]
                episode_id = parse_qs(parsed.query).get("episode_id", ["ep001"])[0]
                self._json(services.load_project(self.workspace, title, episode_id))
            elif parsed.path == "/api/manuscript/load":
                title = parse_qs(parsed.query).get("title", [services.DEFAULT_TITLE])[0]
                self._json({"ok": True, **services.load_manuscript(self.workspace, title)})
            elif parsed.path == "/api/manuscript/chunks":
                title = parse_qs(parsed.query).get("title", [services.DEFAULT_TITLE])[0]
                self._json({"ok": True, **services.list_chunks(self.workspace, title)})
            elif parsed.path == "/api/episodes":
                title = parse_qs(parsed.query).get("title", [services.DEFAULT_TITLE])[0]
                self._json({"ok": True, **services.list_episodes(self.workspace, title)})
            elif parsed.path == "/api/episode/load":
                query = parse_qs(parsed.query)
                title = query.get("title", [services.DEFAULT_TITLE])[0]
                episode_id = query.get("episode_id", ["ep001"])[0]
                self._json({"ok": True, **services.load_episode(self.workspace, title, episode_id)})
            elif parsed.path == "/api/assets/inspect":
                query = parse_qs(parsed.query)
                title = query.get("title", [services.DEFAULT_TITLE])[0]
                episode_id = query.get("episode_id", ["ep001"])[0]
                self._json({"ok": True, **services.inspect_assets(self.workspace, title, episode_id)})
            elif parsed.path.startswith("/media/"):
                self._serve_media(parsed.path)
            elif parsed.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
            else:
                self._json({"ok": False, "error": "not found"}, 404)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self._body()
            title = str(payload.get("title", services.DEFAULT_TITLE)).strip() or services.DEFAULT_TITLE
            idea = str(payload.get("idea", services.DEFAULT_IDEA)).strip() or services.DEFAULT_IDEA
            scenario = str(payload.get("scenario", services.DEFAULT_SCENARIO)) or services.DEFAULT_SCENARIO
            voice = str(payload.get("voice", "Microsoft Heami Desktop")) or "Microsoft Heami Desktop"
            burn_subtitles = bool(payload.get("burn_subtitles", True))
            episode_id = str(payload.get("episode_id", "ep001")) or "ep001"

            if parsed.path == "/api/project/save":
                self._json({"ok": True, **services.save_project(self.workspace, title, idea, scenario)})
            elif parsed.path == "/api/manuscript/save":
                manuscript = str(payload.get("manuscript", ""))
                self._json({"ok": True, **services.save_manuscript(self.workspace, title, idea, manuscript)})
            elif parsed.path == "/api/manuscript/split":
                target_chars = int(payload.get("target_chars", 2500) or 2500)
                self._json({"ok": True, **services.split_manuscript(self.workspace, title, target_chars)})
            elif parsed.path == "/api/episode/create-from-chunk":
                chunk_id = str(payload.get("chunk_id", ""))
                new_episode_id = str(payload.get("episode_id", "ep001")) or "ep001"
                self._json({"ok": True, **services.create_episode_from_chunk(self.workspace, title, chunk_id, new_episode_id)})
            elif parsed.path == "/api/episode/save":
                episode_title = str(payload.get("episode_title", episode_id))
                self._json({"ok": True, **services.save_episode(self.workspace, title, episode_id, scenario, episode_title)})
            elif parsed.path == "/api/scenario/build":
                self._json({"ok": True, **services.build_pipeline(self.workspace, title, idea, scenario, episode_id)})
            elif parsed.path == "/api/tts/synth":
                self._json({"ok": True, **services.synth_tts(self.workspace, title, voice, episode_id)})
            elif parsed.path == "/api/preview/render":
                self._json({"ok": True, **services.render_preview_video(self.workspace, title, burn_subtitles, episode_id)})
            elif parsed.path == "/api/assets/inspect":
                self._json({"ok": True, **services.inspect_assets(self.workspace, title, episode_id)})
            elif parsed.path == "/api/make/all":
                self._json({"ok": True, **services.make_all(self.workspace, title, idea, scenario, voice, burn_subtitles, episode_id)})
            else:
                self._json({"ok": False, "error": "not found"}, 404)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    def _serve_media(self, path_text: str) -> None:
        rel = unquote(path_text[len("/media/"):])
        path = (self.workspace / "local_projects" / rel).resolve()
        root = (self.workspace / "local_projects").resolve()
        if not str(path).startswith(str(root)) or not path.exists() or not path.is_file():
            self._json({"ok": False, "error": "media not found"}, 404)
            return
        content_type = "video/mp4" if path.suffix.lower() == ".mp4" else "application/octet-stream"
        self._file(path, content_type)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Run magicStudio separated web app")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7870)
    args = parser.parse_args()
    MagicStudioHandler.workspace = Path(args.workspace).resolve()
    server = ThreadingHTTPServer((args.host, args.port), MagicStudioHandler)
    print("=== magicStudio Web App ===")
    print(f"workspace: {MagicStudioHandler.workspace}")
    print(f"url: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutdown")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
