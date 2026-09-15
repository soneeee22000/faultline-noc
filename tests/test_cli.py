"""Tests for the command-line entry point."""

import pytest

from faultline_noc.__main__ import main


def test_smoke_exits_zero_and_prints_the_report(capsys: pytest.CaptureFixture[str]) -> None:
    """The smoke run passes the harness check and prints accuracy and the matrix."""
    exit_code = main(["--smoke"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Detection matrix" in output
    assert "s01_upf_crashloop" in output
    assert "PASS" in output


def test_a_mode_is_required() -> None:
    """Running without --smoke or --all is a usage error."""
    with pytest.raises(SystemExit):
        main([])


def test_seed_count_must_be_positive() -> None:
    """A non-positive seed count is a usage error."""
    with pytest.raises(SystemExit):
        main(["--all", "--seeds", "0"])
