"""Interactive web server for verified optimization agents (standard library only).

Serves a single-page interface on 127.0.0.1 and exposes a JSON endpoint for solving
interactive optimization problems with automated verification.
"""

import argparse
import http.server
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .interactive import solve_interactive_problem
from .llm import LLM, make_llm

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"
MAX_POST_BODY_BYTES = 20000


class WebRequestHandler(http.server.BaseHTTPRequestHandler):
    """Handles GET / for the interface page and POST /api/solve for solving problems."""

    server: "WebServer"

    def do_GET(self) -> None:
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

    def do_POST(self) -> None:
        if self.path != "/api/solve":
            self.send_error(404, "Not Found")
            return

        content_length_str = self.headers.get("Content-Length")
        if not content_length_str or not content_length_str.isdigit():
            self.send_error(400, "Missing or invalid Content-Length")
            return

        content_length = int(content_length_str)
        if content_length > MAX_POST_BODY_BYTES:
            self.send_error(413, f"Request body too large (maximum {MAX_POST_BODY_BYTES} bytes)")
            return

        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_error(400, "Invalid JSON in request body")
            return

        if not isinstance(payload, dict):
            self.send_error(400, "Request body must be a JSON object")
            return

        question = payload.get("question")
        if not question or not isinstance(question, str) or not question.strip():
            self.send_error(400, "Missing or empty question")
            return

        raw_threshold = payload.get("threshold", 0.8)
        try:
            threshold = float(raw_threshold)
        except (TypeError, ValueError):
            self.send_error(400, "Threshold must be a float")
            return

        if not (0.0 <= threshold <= 1.0):
            self.send_error(400, "Threshold must be between 0.0 and 1.0")
            return

        try:
            record = solve_interactive_problem(
                question,
                self.server.llm,
                threshold=threshold,
            )
        except ValueError as err:
            self.send_error(400, str(err))
            return
        except Exception as err:
            self.send_error(500, f"Pipeline error: {err}")
            return

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
            "threshold": threshold,
        }

        response_bytes = json.dumps(response_dict).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def log_message(self, format: str, *args: object) -> None:
        """Keep standard output clean unless debugging."""
        pass


class WebServer(http.server.ThreadingHTTPServer):
    """Threading HTTP server with bound LLM instance."""

    def __init__(self, server_address: tuple[str, int], RequestHandlerClass: type[http.server.BaseHTTPRequestHandler], llm: LLM):
        super().__init__(server_address, RequestHandlerClass)
        self.llm = llm


def make_server(host: str, port: int, llm: LLM) -> WebServer:
    """Create a server bound strictly to 127.0.0.1."""
    if host != "127.0.0.1":
        raise ValueError("Server must bind to 127.0.0.1 only.")
    return WebServer((host, port), WebRequestHandler, llm)


def _validate_api_credentials(model_spec: str) -> None:
    """Ensure required environment variables for the selected model exist."""
    provider, _, _ = model_spec.partition(":")
    if provider == "bedrock":
        has_token = bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK"))
        has_access_keys = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
        has_profile = bool(os.getenv("AWS_PROFILE"))
        if not (has_token or has_access_keys or has_profile):
            sys.exit(
                "Error: No Amazon Bedrock credentials found. "
                "Set AWS_BEARER_TOKEN_BEDROCK, AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY, "
                "or AWS_PROFILE in .env."
            )
    elif provider == "openai":
        if not os.getenv("LLM_BASE_URL"):
            sys.exit("Error: LLM_BASE_URL is not set in .env.")
        base_url = os.getenv("LLM_BASE_URL", "")
        if "localhost" not in base_url and "127.0.0.1" not in base_url and not os.getenv("LLM_API_KEY"):
            sys.exit("Error: LLM_API_KEY is not set in .env.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Start the interactive web server for verified optimization agents.")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default 8000)")
    parser.add_argument("--model", default="bedrock:openai.gpt-oss-120b-1:0", help="model specification")
    parser.add_argument("--env-file", default=".env", help="environment file path")
    args = parser.parse_args(argv)

    load_dotenv(args.env_file, override=False)
    _validate_api_credentials(args.model)
    llm = make_llm(args.model)

    server = make_server("127.0.0.1", args.port, llm)
    print(f"Interactive interface serving at http://127.0.0.1:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()


if __name__ == "__main__":
    main()
