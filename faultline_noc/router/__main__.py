"""Command-line entry point: python -m faultline_noc.router --smoke | --all [--json PATH]."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from faultline_noc.paths import REPO_ROOT
from faultline_noc.router.challenge import DEFAULT_CHALLENGE_PATH, load_challenge, smoke_subset
from faultline_noc.router.export import RunLabels, build_payload, write_payload
from faultline_noc.router.harness import BASELINE_NAME, default_routers, harness_failures
from faultline_noc.router.metrics import compute_metrics
from faultline_noc.router.report import render_report
from faultline_noc.router.runner import run_routers

EXIT_OK = 0
EXIT_HARNESS_FAILURE = 1
COMMAND_PREFIX = "python -m faultline_noc.router"


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(prog="faultline_noc.router", description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--smoke", action="store_true", help="the first challenge item carrying each tag"
    )
    mode.add_argument("--all", action="store_true", help="every challenge item")
    parser.add_argument("--challenge", type=Path, default=DEFAULT_CHALLENGE_PATH)
    parser.add_argument(
        "--json", type=Path, default=None, metavar="PATH", help="also write the results as JSON"
    )
    return parser.parse_args(argv)


def challenge_label(path: Path) -> str:
    """Return a challenge path relative to the repo root when it is inside it, else absolute."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def command_label(smoke: bool, challenge: Path) -> str:
    """Return the reproducible command, naming --challenge only when it is not the default."""
    command = f"{COMMAND_PREFIX} {'--smoke' if smoke else '--all'}"
    if challenge.resolve() != DEFAULT_CHALLENGE_PATH.resolve():
        command += f" --challenge {challenge_label(challenge)}"
    return command


def main(argv: Sequence[str] | None = None) -> int:
    """Run every router over the set, print the report and return 1 if the harness fails."""
    args = _parse_args(argv)
    smoke = bool(args.smoke)
    challenge = Path(args.challenge)
    everything = load_challenge(challenge)
    items = smoke_subset(everything) if smoke else everything
    routers = default_routers()
    results = run_routers(routers, items)
    metrics = tuple(
        compute_metrics([result for result in results if result.router == router.name], items)
        for router in routers
    )
    failures = harness_failures(results, items)
    print(render_report(results, items, metrics, failures, BASELINE_NAME))
    if args.json is not None:
        labels = RunLabels(
            command=command_label(smoke, challenge),
            baseline=BASELINE_NAME,
            challenge_set=challenge_label(challenge),
        )
        payload = build_payload(results, items, metrics, failures, labels)
        write_payload(Path(args.json), payload)
    return EXIT_HARNESS_FAILURE if failures else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
