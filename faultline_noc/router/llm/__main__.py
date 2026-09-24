"""Command-line entry point: python -m faultline_noc.router.llm --record|--replay SCOPE.

--dev runs the development set the prompt is tuned on. --smoke and --all run the challenge set
and share its cassettes. The spend limit is a stop threshold checked before each call, so the
last call can take the total slightly past it; the report prints what was actually spent.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from faultline_noc.llm.agent import MODEL_PROFILES
from faultline_noc.llm.env import load_env_file
from faultline_noc.llm.pricing import BudgetExceededError, SpendTracker
from faultline_noc.llm.transport import CassetteMissingError
from faultline_noc.paths import DEFAULT_ENV_FILE
from faultline_noc.router.__main__ import challenge_label
from faultline_noc.router.challenge import DEFAULT_CHALLENGE_PATH, load_challenge, smoke_subset
from faultline_noc.router.harness import BASELINE_NAME
from faultline_noc.router.llm.export import LlmRunLabels, build_llm_payload, write_llm_payload
from faultline_noc.router.llm.prompt import prompt_sha256
from faultline_noc.router.llm.run import RunConfig, RunOutput, run_all
from faultline_noc.router.models import ChallengeItem
from faultline_noc.router.report import metric_sections

DEV_SET_PATH = DEFAULT_CHALLENGE_PATH.parent / "dev.yaml"
DEFAULT_MODELS = ("claude-haiku-4-5", "claude-sonnet-5")
SMOKE_MODELS = ("claude-haiku-4-5",)
DEFAULT_BUDGET_USD = 5.0
COMMAND_PREFIX = "python -m faultline_noc.router.llm --replay"
EXIT_OK = 0
EXIT_BUDGET_REACHED = 2
EXIT_CASSETTE_MISSING = 3


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(prog="faultline_noc.router.llm", description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--record", action="store_true", help="call the API, saving every response")
    mode.add_argument("--replay", action="store_true", help="answer only from saved responses")
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--smoke", action="store_true", help="smoke subset, Haiku only")
    scope.add_argument("--dev", action="store_true", help="the prompt-tuning development set")
    scope.add_argument("--all", action="store_true", help="every challenge item")
    parser.add_argument("--models", nargs="+", choices=sorted(MODEL_PROFILES), default=None)
    parser.add_argument("--budget-usd", type=float, default=DEFAULT_BUDGET_USD)
    parser.add_argument("--json", type=Path, default=None, help="write the payload JSON here")
    return parser.parse_args(argv)


def _scope(args: argparse.Namespace) -> tuple[str, Path, tuple[ChallengeItem, ...]]:
    """Return the scope flag, the item file and the items to route."""
    if args.dev:
        return "--dev", DEV_SET_PATH, load_challenge(DEV_SET_PATH)
    items = load_challenge(DEFAULT_CHALLENGE_PATH)
    if args.smoke:
        return "--smoke", DEFAULT_CHALLENGE_PATH, smoke_subset(items)
    return "--all", DEFAULT_CHALLENGE_PATH, items


def _models(args: argparse.Namespace) -> tuple[str, ...]:
    """Return the models to run: the given ones, else Haiku for smoke and both otherwise."""
    if args.models is not None:
        return tuple(args.models)
    return SMOKE_MODELS if args.smoke else DEFAULT_MODELS


def _execute(
    config: RunConfig, items: Sequence[ChallengeItem], spend: SpendTracker
) -> int | RunOutput:
    """Run every router, turning a spend stop or a missing cassette into an exit code."""
    try:
        return run_all(config, items, spend)
    except BudgetExceededError as error:
        print(f"Stopped early: {error}", file=sys.stderr)
        return EXIT_BUDGET_REACHED
    except CassetteMissingError as error:
        print(f"Replay failed closed: {error}", file=sys.stderr)
        return EXIT_CASSETTE_MISSING


def _report(output: RunOutput, items: Sequence[ChallengeItem], spend: SpendTracker) -> str:
    """Return the markdown report: metrics, then malformed answers and spend."""
    results = (*output.baseline_results, *output.model_results)
    malformed = [
        f"- {r.router} on {r.item_id}: {r.malformed}" for r in output.model_results if r.malformed
    ]
    return "\n\n".join(
        (
            "# Faultline LLM router report",
            f"Prompt sha256 {prompt_sha256()}. Spent ${spend.total_usd:.4f}.",
            *metric_sections(results, items, output.metrics),
            "## Malformed answers",
            "\n".join(malformed) or "None.",
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Route the items with each model, print the report and write the payload on success."""
    args = _parse_args(argv)
    flag, path, items = _scope(args)
    if args.record:
        load_env_file(DEFAULT_ENV_FILE)
    config = RunConfig(record=bool(args.record), models=_models(args), dev=bool(args.dev))
    spend = SpendTracker(budget_usd=float(args.budget_usd))
    output = _execute(config, items, spend)
    if isinstance(output, int):
        print(f"Spent ${spend.total_usd:.4f} before stopping.", file=sys.stderr)
        return output
    print(_report(output, items, spend))
    if args.json is not None:
        labels = LlmRunLabels(
            command=f"{COMMAND_PREFIX} {flag} --models {' '.join(config.models)}",
            challenge_set=challenge_label(path),
            baseline=BASELINE_NAME,
            prompt_sha256=prompt_sha256(),
            prompt_tuned_on=challenge_label(DEV_SET_PATH),
            dev_items=len(load_challenge(DEV_SET_PATH)),
        )
        payload = build_llm_payload(
            output.baseline_results, output.model_results, output.records, output.metrics, labels
        )
        write_llm_payload(Path(args.json), payload)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
