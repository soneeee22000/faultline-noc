"""Tests for loading the router challenge set and for the shape of the authored set."""

import re
from collections import Counter
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from faultline_noc.router.challenge import DEFAULT_CHALLENGE_PATH, load_challenge, smoke_subset
from faultline_noc.router.models import Agent, ChallengeItem, Tag

REF_PATTERN = re.compile(r"^(lab|doc|cluster|test-run|test-suite|alarm|ticket|nf):[A-Za-z0-9._-]+$")
MIN_ITEMS, MAX_ITEMS = 45, 60
MIN_PER_TAG = {Tag.SINGLE: 15, Tag.MULTI: 8, Tag.AMBIGUOUS: 5, Tag.WRITE: 6, Tag.INJECTION: 5}
MIN_SINGLE_PER_AGENT = 5


@pytest.fixture(scope="module")
def challenge() -> tuple[ChallengeItem, ...]:
    """Return the committed challenge set."""
    return load_challenge()


def test_the_set_has_about_fifty_items(challenge: tuple[ChallengeItem, ...]) -> None:
    """The set is small enough to author by hand and large enough to exercise every path."""
    assert MIN_ITEMS <= len(challenge) <= MAX_ITEMS


def test_every_tag_is_well_represented(challenge: tuple[ChallengeItem, ...]) -> None:
    """Each tag has a minimum number of items."""
    counts = Counter(tag for item in challenge for tag in item.tags)
    for tag, minimum in MIN_PER_TAG.items():
        assert counts[tag] >= minimum, tag


def test_every_agent_has_single_intent_items(challenge: tuple[ChallengeItem, ...]) -> None:
    """Each specialist is the whole answer for several items."""
    singles = Counter(item.expected.steps[0].agent for item in challenge if Tag.SINGLE in item.tags)
    assert all(singles[agent] >= MIN_SINGLE_PER_AGENT for agent in Agent)


def test_every_ref_is_typed(challenge: tuple[ChallengeItem, ...]) -> None:
    """Refs look like kind:id with a known kind."""
    refs = [ref for item in challenge for ref in item.available_context]
    assert all(REF_PATTERN.match(ref) for ref in refs), [
        r for r in refs if not REF_PATTERN.match(r)
    ]


def test_some_later_step_needs_a_handed_off_ref(challenge: tuple[ChallengeItem, ...]) -> None:
    """At least one multi-step item requires context on a step after the first."""
    assert any(step.context_refs for item in challenge for step in item.expected.steps[1:])


def test_the_smoke_subset_is_the_first_item_of_each_tag(
    challenge: tuple[ChallengeItem, ...],
) -> None:
    """Smoke keeps one item per tag, in set order, and every tag is covered."""
    subset = smoke_subset(challenge)
    assert len(subset) <= len(Tag)
    assert {tag for item in subset for tag in item.tags} == set(Tag)
    for tag in Tag:
        first = next(item for item in challenge if tag in item.tags)
        assert first in subset


def test_a_missing_file_raises(tmp_path: Path) -> None:
    """Loading a path that does not exist fails loudly."""
    with pytest.raises(FileNotFoundError):
        load_challenge(tmp_path / "missing.yaml")


def test_an_invalid_item_is_rejected(tmp_path: Path) -> None:
    """A write request tagged as single-only fails validation on load."""
    path = tmp_path / "challenge.yaml"
    path.write_text(
        "schema_version: 1\nitems:\n"
        "  - id: r01_bad\n    request: Restart amf-1.\n    available_context: []\n"
        "    tags: [single]\n    expected:\n      requires_clarification: false\n"
        "      steps:\n        - {agent: incident, network_write: true}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_challenge(path)


def test_the_default_path_is_outside_the_scenario_glob() -> None:
    """The set lives in a subdirectory, so the RCA scenario loader never picks it up."""
    assert DEFAULT_CHALLENGE_PATH.parent.name == "router"
    assert DEFAULT_CHALLENGE_PATH.parent.parent.name == "scenarios"


def test_a_duplicated_key_is_rejected(tmp_path: Path) -> None:
    """A copy-paste slip that repeats a key fails the load instead of keeping the last value."""
    path = tmp_path / "challenge.yaml"
    path.write_text(
        "schema_version: 1\nitems:\n"
        "  - id: r01_dup\n    request: Explain the AMF.\n    request: Restart amf-1 now.\n"
        "    available_context: []\n    tags: [single]\n    expected:\n"
        "      requires_clarification: false\n      steps:\n        - {agent: knowledge}\n",
        encoding="utf-8",
    )
    with pytest.raises(yaml.YAMLError, match="request"):
        load_challenge(path)
