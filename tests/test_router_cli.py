"""Tests for the router command-line entry point and its JSON export."""

from pathlib import Path

import pytest

from faultline_noc.paths import REPO_ROOT
from faultline_noc.router.__main__ import main
from faultline_noc.router.challenge import DEFAULT_CHALLENGE_PATH
from faultline_noc.router.export import RouterPayload, payload_json
from faultline_noc.router.harness import BASELINE_NAME

COMMITTED_JSON = REPO_ROOT / "site" / "src" / "data" / "router_results.json"


def test_smoke_exits_zero_and_prints_the_report(capsys: pytest.CaptureFixture[str]) -> None:
    """The smoke run passes the harness check and prints metrics and the matrix."""
    exit_code = main(["--smoke"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "## Route metrics" in output
    assert "## Detection matrix" in output
    assert BASELINE_NAME in output
    assert "PASS" in output


def test_all_writes_a_json_payload_that_round_trips(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--all --json writes a valid payload whose verdict matches the exit code."""
    path = tmp_path / "out" / "router_results.json"
    exit_code = main(["--all", "--json", str(path)])
    capsys.readouterr()
    payload = RouterPayload.model_validate_json(path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload.meta.harness_pass
    assert payload.meta.command == "python -m faultline_noc.router --all"
    assert payload_json(payload) == path.read_text(encoding="utf-8")
    assert len(payload.outcomes) == payload.meta.items * len(payload.meta.routers)


def test_output_is_deterministic(capsys: pytest.CaptureFixture[str]) -> None:
    """Two runs print byte-identical reports."""
    main(["--all"])
    first = capsys.readouterr().out
    main(["--all"])
    assert capsys.readouterr().out == first


def test_committed_json_matches_a_fresh_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The committed site data is what --all produces today."""
    path = tmp_path / "router_results.json"
    main(["--all", "--json", str(path)])
    capsys.readouterr()
    assert path.read_bytes() == COMMITTED_JSON.read_bytes()


def test_a_mode_is_required() -> None:
    """Running without --smoke or --all is a usage error."""
    with pytest.raises(SystemExit):
        main([])


def test_modes_are_mutually_exclusive() -> None:
    """--smoke and --all cannot be combined."""
    with pytest.raises(SystemExit):
        main(["--smoke", "--all"])


def test_a_non_default_challenge_file_is_recorded_in_the_payload(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--challenge PATH shows up in the reproducible command and in meta.challenge_set."""
    source = tmp_path / "other.yaml"
    source.write_bytes(DEFAULT_CHALLENGE_PATH.read_bytes())
    path = tmp_path / "router_results.json"
    main(["--all", "--challenge", str(source), "--json", str(path)])
    capsys.readouterr()
    payload = RouterPayload.model_validate_json(path.read_text(encoding="utf-8"))
    assert payload.meta.challenge_set == source.resolve().as_posix()
    assert payload.meta.command == (
        f"python -m faultline_noc.router --all --challenge {source.resolve().as_posix()}"
    )


def test_the_default_challenge_file_is_recorded_relative_to_the_repo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Passing the default path explicitly gives the same labels as leaving it out."""
    path = tmp_path / "router_results.json"
    main(["--all", "--challenge", str(DEFAULT_CHALLENGE_PATH), "--json", str(path)])
    capsys.readouterr()
    payload = RouterPayload.model_validate_json(path.read_text(encoding="utf-8"))
    assert payload.meta.challenge_set == "scenarios/router/challenge.yaml"
    assert payload.meta.command == "python -m faultline_noc.router --all"
