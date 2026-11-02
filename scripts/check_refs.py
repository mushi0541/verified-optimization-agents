"""Validate paper references in BibTeX and cross-reference with LaTeX citations (#43).

    python scripts/check_refs.py [--bib docs/paper/refs.bib] [--tex docs/paper/main.tex] [--min-entries 30]

Verifies that:
- Every BibTeX entry has a title, author, year, and a DOI or official URL.
- Every entry in the BibTeX file is cited in the LaTeX manuscript.
- Every citation key used in the LaTeX manuscript is defined in the BibTeX file.
- The total number of valid entries meets or exceeds the required threshold (default: 30).
"""

import argparse
import re
import sys
from pathlib import Path

REQUIRED_FIELDS = ("title", "author", "year")


def parse_bibtex(bib_text: str) -> dict[str, dict]:
    """Parse BibTeX text into a dictionary of {key: fields_dict}.

    Extracts entry type, citation key, and key-value fields.
    """
    entries = {}
    # Find each entry: @type{key, ...
    entry_pattern = re.compile(r"@(\w+)\s*\{\s*([^,]+),", re.MULTILINE)
    matches = list(entry_pattern.finditer(bib_text))
    for i, match in enumerate(matches):
        entry_type = match.group(1).lower()
        if entry_type in ("comment", "string", "preamble"):
            continue
        key = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(bib_text)
        block = bib_text[start:end]

        fields = {"_type": entry_type}
        # Parse fields: name = {val} or name = "val" or name = 123
        field_matches = re.finditer(
            r'([a-zA-Z_][a-zA-Z0-9_-]*)\s*=\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\}|"([^"]*)"|([0-9]+))',
            block,
            re.DOTALL,
        )
        for fm in field_matches:
            fname = fm.group(1).lower()
            val = fm.group(2) if fm.group(2) is not None else (fm.group(3) if fm.group(3) is not None else fm.group(4))
            fields[fname] = val.strip() if val else ""
        entries[key] = fields
    return entries


def extract_citations(tex_text: str) -> set[str]:
    """Extract all citation keys referenced in LaTeX text via \\cite{...} commands."""
    citations = set()
    # Match \cite{...}, \citep{...}, \citet{...}, \citeauthor{...}, etc.
    cite_matches = re.findall(r"\\cite[a-zA-Z]*\{([^}]+)\}", tex_text)
    for block in cite_matches:
        for key in block.split(","):
            cleaned = key.strip()
            if cleaned:
                citations.add(cleaned)
    return citations


def check_entries(entries: dict[str, dict], min_entries: int = 30) -> list[str]:
    """Check that BibTeX entries have required fields, valid links, and meet the minimum count."""
    errors = []
    if len(entries) < min_entries:
        errors.append(f"Found {len(entries)} entries in BibTeX, but at least {min_entries} are required.")

    for key, fields in entries.items():
        for req in REQUIRED_FIELDS:
            if not fields.get(req):
                errors.append(f"Entry '{key}' is missing required field '{req}'.")
        has_doi = bool(fields.get("doi"))
        has_url = bool(fields.get("url"))
        if not (has_doi or has_url):
            errors.append(f"Entry '{key}' has neither DOI nor URL link.")
    return errors


def cross_reference(bib_keys: set[str], tex_citations: set[str]) -> tuple[set[str], set[str]]:
    """Return (uncited_keys, missing_keys)."""
    uncited = bib_keys - tex_citations
    missing = tex_citations - bib_keys
    return uncited, missing


def validate_references(bib_path: Path, tex_path: Path, min_entries: int = 30) -> tuple[bool, list[str]]:
    """Validate BibTeX entries and cross-reference with LaTeX file.

    Returns (is_valid, list_of_messages).
    """
    messages = []
    if not bib_path.exists():
        return False, [f"BibTeX file does not exist: {bib_path}"]
    if not tex_path.exists():
        return False, [f"LaTeX file does not exist: {tex_path}"]

    bib_text = bib_path.read_text(encoding="utf-8")
    tex_text = tex_path.read_text(encoding="utf-8")

    entries = parse_bibtex(bib_text)
    tex_citations = extract_citations(tex_text)
    bib_keys = set(entries.keys())

    messages.append(f"BibTeX entries: {len(bib_keys)}")
    messages.append(f"LaTeX citations: {len(tex_citations)}")

    errors = check_entries(entries, min_entries=min_entries)
    uncited, missing = cross_reference(bib_keys, tex_citations)

    if uncited:
        errors.append(f"BibTeX entries not cited in LaTeX ({len(uncited)}): {', '.join(sorted(uncited))}")
    if missing:
        errors.append(f"LaTeX citations missing from BibTeX ({len(missing)}): {', '.join(sorted(missing))}")

    if errors:
        return False, messages + errors
    messages.append(f"All {len(bib_keys)} entries verified and cited.")
    return True, messages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bib", type=Path, default=Path("docs/paper/refs.bib"), help="Path to refs.bib")
    parser.add_argument("--tex", type=Path, default=Path("docs/paper/main.tex"), help="Path to main.tex")
    parser.add_argument("--min-entries", type=int, default=30, help="Minimum required entries (default 30)")
    args = parser.parse_args()

    success, messages = validate_references(args.bib, args.tex, min_entries=args.min_entries)
    for msg in messages:
        if success:
            print(f"[OK] {msg}")
        else:
            print(f"[FAIL] {msg}" if "missing" in msg.lower() or "not cited" in msg.lower() or "required" in msg.lower() else f"[INFO] {msg}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
