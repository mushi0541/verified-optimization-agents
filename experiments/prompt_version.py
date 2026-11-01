"""Prompt versioning and git commit helpers."""

import hashlib
import subprocess

from optverify import prompts


def get_prompt_version() -> str:
    """Compute the SHA-256 hex digest of concatenated prompt templates."""
    template_names = sorted(
        name for name in dir(prompts)
        if name.isupper() and isinstance(getattr(prompts, name), str)
    )
    concatenated = "".join(getattr(prompts, name) for name in template_names)
    return hashlib.sha256(concatenated.encode("utf-8")).hexdigest()


def get_git_commit() -> str:
    """Return the current git commit hash, or 'unknown' if it fails."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return "unknown"
