"""Default locations of the repo's scenario and intended-config files."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIOS_DIR = REPO_ROOT / "scenarios"
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "intended_config.json"
