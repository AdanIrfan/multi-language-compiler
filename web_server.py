"""Local web frontend and compile API for Compiler Studio."""

import json
import os
import sys
import webbrowser
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
MAX_REQUEST_BYTES = 1_000_000
ALLOWED_FRONTEND_ORIGINS = {
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
}

sys.path.insert(0, BASE_DIR)

from c_compiler import CCompiler
from cpp_compiler import CppCompiler
from python_compiler import PythonCompiler

COMPILERS = {
    "C": CCompiler,
    "C++": CppCompiler,
    "Python": PythonCompiler,
}


class CompilerStudioHandler(BaseHTTPRequestHandler):
    server_version = "CompilerStudio/1.0"

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(200, {"status": "ok", "service": "Compiler Studio"})
            return

        files = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
        }
        asset = files.get(path)
        if asset is None:
            self.send_error(404, "Not found")
            return

        filename, content_type = asset
        try:
            with open(os.path.join(FRONTEND_DIR, filename), "rb") as frontend_file:
                content = frontend_file.read()
        except OSError:
            self.send_error(500, "Frontend assets could not be read")
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self' http://127.0.0.1:8000 http://localhost:8000; img-src 'self' data:")
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        if urlparse(self.path).path != "/api/compile":
            self._send_json(404, {"error": "Not found"})
            return

        origin = self.headers.get("Origin")
        if origin not in ALLOWED_FRONTEND_ORIGINS:
            self._send_json(403, {"error": "Frontend origin is not allowed"})
            return

        self.send_response(204)
        self._add_cors_headers(origin)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        if urlparse(self.path).path != "/api/compile":
            self._send_json(404, {"error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return
        if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "Request must be between 1 byte and 1 MB"})
            return

        try:
            request = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Request body must be valid JSON"})
            return

        if not isinstance(request, dict):
            self._send_json(400, {"error": "Request body must be a JSON object"})
            return

        language = request.get("language")
        code = request.get("code")
        if language not in COMPILERS:
            self._send_json(400, {"error": "Choose C, C++, or Python"})
            return
        if not isinstance(code, str) or not code.strip():
            self._send_json(400, {"error": "Enter source code before compiling"})
            return

        output = StringIO()
        try:
            with redirect_stdout(output):
                COMPILERS[language](code).compile()
        except Exception as exc:
            self._send_json(422, {"error": str(exc), "output": output.getvalue()})
            return

        self._send_json(200, {"output": output.getvalue()})

    def _send_json(self, status, payload):
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        origin = self.headers.get("Origin")
        if origin in ALLOWED_FRONTEND_ORIGINS:
            self._add_cors_headers(origin)
        self.end_headers()
        self.wfile.write(content)

    def _add_cors_headers(self, origin):
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")

    def log_message(self, format_string, *args):
        print(f"[Compiler Studio] {self.address_string()} - {format_string % args}")


def run_web_server(port=8000):
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    server = ThreadingHTTPServer(("127.0.0.1", port), CompilerStudioHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"Compiler Studio is running at {url}")
    print("Press Ctrl+C to stop the server.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCompiler Studio stopped.")
    finally:
        server.server_close()
