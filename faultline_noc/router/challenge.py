"""Load and validate the authored router challenge set, and pick its smoke subset."""

from collections.abc import Sequence
from pathlib import Path

import yaml

from faultline_noc.paths import REPO_ROOT
from faultline_noc.router.models import ChallengeItem, ChallengeSet, Tag

DEFAULT_CHALLENGE_PATH = REPO_ROOT / "scenarios" / "router" / "challenge.yaml"


class UniqueKeyLoader(yaml.SafeLoader):
    """A SafeLoader that rejects a mapping with a repeated key instead of keeping the last one."""


def _unique_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode) -> dict[object, object]:
    """Construct a mapping, raising on any key that appears twice in it."""
    keys = [loader.construct_object(key_node) for key_node, _ in node.value]
    repeated = sorted({str(key) for key in keys if keys.count(key) > 1})
    if repeated:
        raise yaml.constructor.ConstructorError(
            None, None, f"duplicate mapping keys {repeated}", node.start_mark
        )
    return loader.construct_mapping(node)


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def load_challenge(path: Path = DEFAULT_CHALLENGE_PATH) -> tuple[ChallengeItem, ...]:
    """Return the validated items of a challenge-set YAML file, in file order."""
    if not path.is_file():
        raise FileNotFoundError(f"no challenge set at {path}")
    document = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    challenge = ChallengeSet.model_validate(document)
    return challenge.items


def smoke_subset(items: Sequence[ChallengeItem]) -> tuple[ChallengeItem, ...]:
    """Return the first item carrying each tag, without duplicates, in set order."""
    chosen = {
        next(item.id for item in items if tag in item.tags)
        for tag in Tag
        if any(tag in item.tags for item in items)
    }
    return tuple(item for item in items if item.id in chosen)
