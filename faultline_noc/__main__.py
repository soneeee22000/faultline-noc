"""Command-line entry point: python -m faultline_noc --smoke | --all."""

import argparse
from collections.abc import Sequence
from pathlib import Path

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
    return parser.parse_args(argv)


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
    selected, seeds = _select(scenarios, smoke=bool(args.smoke), seed_count=int(args.seeds))
    results = run_matrix(selected, topology, seeds)
    failures = harness_failures(results)
    print(render_report(results, seeds, failures))
    return EXIT_HARNESS_FAILURE if failures else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
