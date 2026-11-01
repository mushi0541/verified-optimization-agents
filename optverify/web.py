"""Interactive web server for verified optimization agents (standard library only).

Serves a single-page interface on 127.0.0.1 and exposes a JSON endpoint for solving
interactive optimization problems with automated verification.
"""

import argparse
import http.server
import json
from pathlib import Path

from dotenv import load_dotenv

from .calibration import check_system, threshold_from_file
from .interactive import solve_interactive_problem
from .llm import LLM, make_llm

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"
MAX_POST_BODY_BYTES = 20000


class WebRequestHandler(http.server.BaseHTTPRequestHandler):
    """Handles GET / for the interface page and POST /api/solve for solving problems."""

    server: "WebServer"

    def do_GET(self) -> None:
        if self.path == "/api/config":
            calibration = self.server.calibration
            return self._send_json(200, {
                "alpha": calibration["alpha"] if calibration else None,
                "threshold": calibration["threshold"] if calibration else None,
            })
        if self.path != "/":
            self.send_error(404, "Not Found")
            return

        try:
            content = INDEX_FILE.read_bytes()
        except OSError:
            self.send_error(500, "Could not read interface template")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _local_hosts(self) -> set[str]:
        port = self.server.server_address[1]
        return {f"127.0.0.1:{port}", f"localhost:{port}"}

    def do_POST(self) -> None:
        if self.headers.get("Host") not in self._local_hosts():
            return self._send_json(403, {"error": "Requests must come from this machine."})
        origin = self.headers.get("Origin")
        if origin is not None and origin.removeprefix("http://") not in self._local_hosts():
            return self._send_json(403, {"error": "Requests must come from this page."})
        if self.headers.get_content_type() != "application/json":
            return self._send_json(415, {"error": "Send JSON with Content-Type: application/json."})

        if self.path != "/api/solve":
            return self._send_json(404, {"error": "Not Found"})

        content_length_str = self.headers.get("Content-Length")
        if not content_length_str or not content_length_str.isdigit():
            return self._send_json(400, {"error": "Missing or invalid Content-Length."})

        content_length = int(content_length_str)
        if content_length > MAX_POST_BODY_BYTES:
            return self._send_json(413, {"error": f"Request body too large (maximum {MAX_POST_BODY_BYTES} bytes)."})

        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._send_json(400, {"error": "Invalid JSON in request body."})

        if not isinstance(payload, dict):
            return self._send_json(400, {"error": "Request body must be a JSON object."})

        question = payload.get("question")
        if not question or not isinstance(question, str) or not question.strip():
            return self._send_json(400, {"error": "Missing or empty question."})

        raw_threshold = payload.get("threshold", 0.8)
        try:
            threshold = float(raw_threshold)
        except (TypeError, ValueError):
            return self._send_json(400, {"error": "Threshold must be a float."})

        if not (0.0 <= threshold <= 1.0):
            return self._send_json(400, {"error": "Threshold must be between 0.0 and 1.0."})
        if self.server.calibration:  # a calibrated threshold (Gap 2) overrides the one sent by the page
            threshold = threshold_from_file(self.server.calibration)

        try:
            record = solve_interactive_problem(
                question,
                self.server.llm,
                threshold=threshold,
            )
        except ValueError as err:
            return self._send_json(400, {"error": str(err)})
        except Exception as err:
            return self._send_json(500, {"error": f"Pipeline error: {str(err)}"})

        final_attempt = record.attempts[-1] if record.attempts else None
        solve = final_attempt.solve if final_attempt else None
        variables = (
            [{"name": k, "value": v} for k, v in sorted(solve.variables.items())]
            if solve and solve.variables
            else []
        )

        response_dict = {
            "action": record.decision.action if record.decision else "none",
            "predicted": record.predicted,
            "reasons": record.decision.reasons if record.decision else [],
            "score": record.verifier.score if record.verifier else 0.0,
            "number_coverage": record.verifier.number_coverage if record.verifier else 0.0,
            "missing_numbers": record.verifier.missing_numbers if record.verifier else [],
            "requirement_coverage": record.verifier.requirement_coverage if record.verifier else None,
            "missing_requirements": record.verifier.missing_requirements if record.verifier else [],
            "paraphrase_agreement": record.verifier.paraphrase_agreement if record.verifier else None,
            "paraphrase_objectives": record.verifier.paraphrase_objectives if record.verifier else [],
            "explanation": record.explanation,
            "variables": variables,
            "code": final_attempt.code if final_attempt else "",
            "status": solve.status if solve else "",
            "stdout": solve.stdout if solve else "",
            "error": solve.error if solve else "",
            "usage": {
                "input_tokens": record.usage.input_tokens,
                "output_tokens": record.usage.output_tokens,
                "calls": record.usage.calls,
            } if record.usage else {},
            "latency_s": record.latency_s,
            "threshold": None if threshold == float("inf") else threshold,
            "alpha": self.server.calibration["alpha"] if self.server.calibration else None,
        }
        self._send_json(200, response_dict)

    def log_message(self, format: str, *args: object) -> None:
        """Keep standard output clean unless debugging."""
        pass


class WebServer(http.server.ThreadingHTTPServer):
    """Threading HTTP server with bound LLM instance."""

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[http.server.BaseHTTPRequestHandler],
        llm: LLM,
        calibration: dict | None = None,
    ):
        super().__init__(server_address, RequestHandlerClass)
        self.llm = llm
        self.calibration = calibration


def make_server(host: str, port: int, llm: LLM, calibration: dict | None = None) -> WebServer:
    """Create a server bound strictly to 127.0.0.1."""
    if host != "127.0.0.1":
        raise ValueError("Server must bind to 127.0.0.1 only.")
    return WebServer((host, port), WebRequestHandler, llm, calibration)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Start the interactive web server for verified optimization agents.")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default 8000)")
    parser.add_argument("--model", default="bedrock:openai.gpt-oss-120b-1:0", help="model specification")
    parser.add_argument("--env-file", default=".env", help="environment file path")
    parser.add_argument("--calibration", type=Path, help="calibration file from scripts/calibrate.py (Gap 2)")
    args = parser.parse_args(argv)

    load_dotenv(args.env_file, override=False)
    llm = make_llm(args.model)
    calibration = json.loads(args.calibration.read_text(encoding="utf-8")) if args.calibration else None
    if calibration:
        try:
            check_system(calibration, "pipeline")  # the interface runs the pipeline
        except ValueError as error:
            parser.error(str(error))

    server = make_server("127.0.0.1", args.port, llm, calibration)
    print(f"Interactive interface serving at http://127.0.0.1:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()


if __name__ == "__main__":
    main()
