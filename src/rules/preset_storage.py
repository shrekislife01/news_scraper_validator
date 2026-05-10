from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from .preset import RulePreset, make_preset
from .model import Rule

PRESETS_DIR = Path(__file__).parent.parent.parent / "presets"
RULES_DIR = Path(__file__).parent.parent.parent / "rules"


def save_preset(preset: RulePreset) -> Path:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    path = PRESETS_DIR / f"{preset.id}.json"
    payload = dataclasses.asdict(preset)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_preset(path: Path) -> RulePreset:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return RulePreset(
        id=raw["id"],
        name=raw["name"],
        created_at=raw["created_at"],
        rules=raw.get("rules", []),
    )


def list_presets() -> list[RulePreset]:
    if not PRESETS_DIR.exists():
        return []
    presets = []
    for p in PRESETS_DIR.glob("*.json"):
        try:
            presets.append(load_preset(p))
        except Exception:
            pass
    return sorted(presets, key=lambda p: p.created_at, reverse=True)


def delete_preset(preset_id: str) -> None:
    path = PRESETS_DIR / f"{preset_id}.json"
    if path.exists():
        path.unlink()


def apply_preset(preset: RulePreset) -> None:
    """Replace current rules/ directory contents with the preset's rule snapshots."""
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    for existing in RULES_DIR.glob("*.json"):
        existing.unlink()
    for rule_dict in preset.rules:
        rule = Rule(
            id=rule_dict["id"],
            name=rule_dict["name"],
            scope=rule_dict["scope"],
            action=rule_dict["action"],
            description=rule_dict.get("description"),
            pattern=rule_dict.get("pattern"),
            replacement=rule_dict.get("replacement"),
            value=rule_dict.get("value"),
            domain=rule_dict.get("domain"),
            priority=rule_dict.get("priority", 50),
            enabled=rule_dict.get("enabled", True),
            created_at=rule_dict.get("created_at", ""),
        )
        path = RULES_DIR / f"{rule.id}.json"
        path.write_text(
            json.dumps(dataclasses.asdict(rule), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
