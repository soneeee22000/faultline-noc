"""Regenerate the project page's data from real runs of this repo's code.

Writes site/src/data/results.json from `python -m faultline_noc --all`,
site/src/data/llm_results.json from a replay of the committed cassettes,
site/src/data/router_results.json from `python -m faultline_noc.router --all`, and the stdout of
the smoke run, pytest and mypy to site/src/data/transcripts/. Each transcript starts with one header
line naming the command, the Python version and the date it was captured.
"""

import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "site" / "src" / "data"
RESULTS_PATH = DATA_DIR / "results.json"
LLM_RESULTS_PATH = DATA_DIR / "llm_results.json"
ROUTER_RESULTS_PATH = DATA_DIR / "router_results.json"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
LLM_SEED_COUNT = "3"
EXIT_OK = 0


@dataclass(frozen=True)
class Transcript:
    """A command whose real stdout is saved for the page, and how it is shown."""

    file_name: str
    shown_command: str
    arguments: tuple[str, ...]


TRANSCRIPTS: tuple[Transcript, ...] = (
    Transcript("smoke.txt", "python -m faultline_noc --smoke", ("-m", "faultline_noc", "--smoke")),
    Transcript("pytest.txt", "pytest", ("-m", "pytest")),
    Transcript("mypy.txt", "mypy --strict", ("-m", "mypy", "--strict")),
)


def run_python(arguments: tuple[str, ...]) -> str:
    """Run this interpreter with arguments in the repo root and return stdout, failing loudly."""
    completed = subprocess.run(
        [sys.executable, *arguments],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    if completed.returncode != EXIT_OK:
        sys.stderr.write(completed.stdout + completed.stderr)
        raise SystemExit(f"command failed with exit code {completed.returncode}: {arguments}")
    return completed.stdout


def transcript_header(shown_command: str, python_version: str, captured_on: date) -> str:
    """Return the single header line that opens a transcript."""
    return f"# $ {shown_command} | Python {python_version} | {captured_on.isoformat()}"


def write_results() -> None:
    """Write results.json from a full run of every scenario at every default seed."""
    run_python(("-m", "faultline_noc", "--all", "--json", str(RESULTS_PATH)))
    print(f"wrote {RESULTS_PATH.relative_to(REPO_ROOT).as_posix()}")


def write_llm_results() -> None:
    """Write llm_results.json by replaying the committed cassettes, which needs no API key."""
    arguments = ("-m", "faultline_noc.llm", "--replay", "--seeds", LLM_SEED_COUNT)
    run_python((*arguments, "--json", str(LLM_RESULTS_PATH)))
    print(f"wrote {LLM_RESULTS_PATH.relative_to(REPO_ROOT).as_posix()}")


def write_router_results() -> None:
    """Write router_results.json from a full run of the router challenge set."""
    run_python(("-m", "faultline_noc.router", "--all", "--json", str(ROUTER_RESULTS_PATH)))
    print(f"wrote {ROUTER_RESULTS_PATH.relative_to(REPO_ROOT).as_posix()}")


def write_transcript(transcript: Transcript, captured_on: date) -> None:
    """Run one transcript command and save its header and stdout with LF line endings."""
    stdout = run_python(transcript.arguments)
    header = transcript_header(transcript.shown_command, platform.python_version(), captured_on)
    path = TRANSCRIPTS_DIR / transcript.file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{header}\n{stdout.rstrip()}\n", encoding="utf-8", newline="\n")
    print(f"wrote {path.relative_to(REPO_ROOT).as_posix()}")


def main() -> int:
    """Refresh results.json, llm_results.json, router_results.json and every transcript."""
    write_results()
    write_llm_results()
    write_router_results()
    captured_on = date.today()
    for transcript in TRANSCRIPTS:
        write_transcript(transcript, captured_on)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
