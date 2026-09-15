"""Command-line entry point: python -m faultline_noc.llm --record | --replay [--smoke]."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from faultline_noc.llm.env import load_env_file
from faultline_noc.llm.evaluate import (
    EvalConfig,
    build_payload,
    new_spend_tracker,
    run_evaluation,
)
from faultline_noc.llm.pricing import PRICES, BudgetExceededError, SpendTracker
from faultline_noc.llm.report import render_markdown
from faultline_noc.llm.transport import CassetteMissingError
from faultline_noc.paths import (
    DEFAULT_CASSETTES_DIR,
    DEFAULT_CONFIG_PATH,
    DEFAULT_ENV_FILE,
    DEFAULT_HARD_SCENARIOS_DIR,
    DEFAULT_SCENARIOS_DIR,
)
from faultline_noc.runner import RunResult
from faultline_noc.scenario import Scenario, check_against_topology, load_scenarios
from faultline_noc.topology import Topology, build_topology, load_intended_config

DEFAULT_MODELS = ("claude-haiku-4-5", "claude-sonnet-5")
DEFAULT_SEED_COUNT = 3
DEFAULT_BUDGET_USD = 10.0
SMOKE_MODEL = "claude-haiku-4-5"
SMOKE_SCENARIO = "s01_upf_crashloop"
SMOKE_SEED = 0
EXIT_OK = 0
EXIT_BUDGET_REACHED = 2
EXIT_CASSETTE_MISSING = 3


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(prog="faultline_noc.llm", description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--record", action="store_true", help="call the API, saving every response")
    mode.add_argument("--replay", action="store_true", help="answer only from saved responses")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help=f"{SMOKE_SCENARIO} at seed {SMOKE_SEED} on {SMOKE_MODEL}",
    )
    parser.add_argument("--models", nargs="+", choices=sorted(PRICES), default=list(DEFAULT_MODELS))
    parser.add_argument("--seeds", type=int, default=DEFAULT_SEED_COUNT, help="seeds per scenario")
    parser.add_argument("--budget-usd", type=float, default=DEFAULT_BUDGET_USD)
    parser.add_argument("--json", type=Path, default=None, help="write the payload JSON here")
    return parser.parse_args(argv)


def _config(args: argparse.Namespace) -> EvalConfig:
    """Build the evaluation config; smoke narrows it to one model and one seed."""
    smoke = bool(args.smoke)
    return EvalConfig(
        mode="record" if args.record else "replay",
        models=(SMOKE_MODEL,) if smoke else tuple(args.models),
        seeds=(SMOKE_SEED,) if smoke else tuple(range(int(args.seeds))),
        budget_usd=float(args.budget_usd),
        cassettes_dir=DEFAULT_CASSETTES_DIR,
    )


def _scenarios(topology: Topology, *, smoke: bool) -> tuple[Scenario, ...]:
    """Load the published and hard scenarios, or only the smoke scenario."""
    loaded = (*load_scenarios(DEFAULT_SCENARIOS_DIR), *load_scenarios(DEFAULT_HARD_SCENARIOS_DIR))
    for scenario in loaded:
        check_against_topology(scenario, topology)
    if smoke:
        return tuple(scenario for scenario in loaded if scenario.id == SMOKE_SCENARIO)
    return loaded


def _run(
    config: EvalConfig,
    scenarios: Sequence[Scenario],
    topology: Topology,
    results: list[RunResult],
    spend: SpendTracker,
) -> int:
    """Run the evaluation, turning a spend stop or a missing cassette into an exit code."""
    try:
        run_evaluation(config, scenarios, topology, results, spend)
    except BudgetExceededError as error:
        print(f"Stopped early: {error}", file=sys.stderr)
        return EXIT_BUDGET_REACHED
    except CassetteMissingError as error:
        print(f"Replay failed closed: {error}", file=sys.stderr)
        return EXIT_CASSETTE_MISSING
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Run the evaluation, print the report, and write the payload when the run completed."""
    args = _parse_args(argv)
    config = _config(args)
    if config.mode == "record":
        load_env_file(DEFAULT_ENV_FILE)
    topology = build_topology(load_intended_config(DEFAULT_CONFIG_PATH))
    scenarios = _scenarios(topology, smoke=bool(args.smoke))
    results: list[RunResult] = []
    spend = new_spend_tracker(config)
    code = _run(config, scenarios, topology, results, spend)
    payload = build_payload(config, scenarios, results, spend)
    print(render_markdown(payload))
    if args.json is not None and code == EXIT_OK:
        args.json.write_bytes((payload.model_dump_json(indent=2) + "\n").encode("utf-8"))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
