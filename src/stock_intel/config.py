from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"


def load_yaml(name: str, config_dir: Path = CONFIG_DIR) -> dict:
    path = config_dir / name
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_universe_config(config_dir: Path = CONFIG_DIR) -> dict:
    return load_yaml("universe.yaml", config_dir)


def load_exclusions_config(config_dir: Path = CONFIG_DIR) -> dict:
    return load_yaml("exclusions.yaml", config_dir)


def load_scoring_config(config_dir: Path = CONFIG_DIR) -> dict:
    cfg = load_yaml("scoring_weights.yaml", config_dir)
    weights = cfg.get("weights", {})
    total = sum(weights.values())
    if weights and abs(total - 1.0) > 1e-6:
        raise ValueError(f"scoring_weights.yaml weights must sum to 1.0, got {total}")
    return cfg


def load_macro_exposure_config(config_dir: Path = CONFIG_DIR) -> dict:
    return load_yaml("macro_exposure.yaml", config_dir)
