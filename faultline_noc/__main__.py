"""Command-line entry point: python -m faultline_noc --smoke | --all [--json PATH]."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from faultline_noc.export import build_payload, write_payload
from faultline_noc.paths import DEFAULT_CONFIG_PATH, DEFAULT_SCENARIOS_DIR
from faultline_noc.report import render_report
from faultline_noc.runner import run_matrix
from faultline_noc.scenario import Scenario, check_against_topology, load_scenarios
from faultline_noc.scoring import harness_failures
from faultline_noc.topology import build_topology, load_intended_config

SMOKE_SEED = 0
DEFAULT_SEED_COUNT = 200
EXIT_OK = 0
EXIT_HARNESS_FAILURE = 1
COMMAND_PREFIX = "python -m faultline_noc"


def _positive_int(text: str) -> int:
    """Parse a strictly positive integer for argparse."""
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(prog="faultline_noc", description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--smoke", action="store_true", help=f"every scenario at seed {SMOKE_SEED} only"
    )
    mode.add_argument("--all", action="store_true", help="every scenario at every seed")
    parser.add_argument(
        "--seeds", type=_positive_int, default=DEFAULT_SEED_COUNT, help="seed count for --all"
    )
    parser.add_argument("--scenarios-dir", type=Path, default=DEFAULT_SCENARIOS_DIR)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--json", type=Path, default=None, metavar="PATH", help="also write the results as JSON"
    )
    return parser.parse_args(argv)


def _command_label(smoke: bool, seed_count: int) -> str:
    """Return the reproducible command for the run, without output paths."""
    if smoke:
        return f"{COMMAND_PREFIX} --smoke"
    if seed_count == DEFAULT_SEED_COUNT:
        return f"{COMMAND_PREFIX} --all"
    return f"{COMMAND_PREFIX} --all --seeds {seed_count}"


def _select(
    scenarios: Sequence[Scenario], smoke: bool, seed_count: int
) -> tuple[tuple[Scenario, ...], tuple[int, ...]]:
    """Return the scenarios and seeds for the mode; smoke keeps every scenario at one seed."""
    if smoke:
        return tuple(scenarios), (SMOKE_SEED,)
    return tuple(scenarios), tuple(range(seed_count))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the eval, print the markdown report and return a non-zero code if the harness fails."""
    args = _parse_args(argv)
    topology = build_topology(load_intended_config(args.config))
    scenarios = load_scenarios(args.scenarios_dir)
    for scenario in scenarios:
        check_against_topology(scenario, topology)
    smoke, seed_count = bool(args.smoke), int(args.seeds)
    selected, seeds = _select(scenarios, smoke=smoke, seed_count=seed_count)
    results = run_matrix(selected, topology, seeds)
    failures = harness_failures(results)
    print(render_report(results, seeds, failures))
    if args.json is not None:
        command = _command_label(smoke, seed_count)
        payload = build_payload(results, seeds, failures, selected, topology, command=command)
        write_payload(Path(args.json), payload)
    return EXIT_HARNESS_FAILURE if failures else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
