from __future__ import annotations

import dataclasses
import gzip
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .model import PipelineResult, Rule

RULES_DIR = Path(__file__).parent.parent.parent / "rules"
PIPELINE_RESULTS_DIR = Path(__file__).parent.parent.parent / "pipeline_results"
HTML_CACHE_DIR = Path(__file__).parent.parent.parent / "html_cache"


def save_rule(rule: Rule) -> Path:
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    path = RULES_DIR / f"{rule.id}.json"
    payload = dataclasses.asdict(rule)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_rule(path: Path) -> Rule:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Rule(
        id=raw["id"],
        name=raw["name"],
        scope=raw["scope"],
        action=raw["action"],
        description=raw.get("description"),
        pattern=raw.get("pattern"),
        replacement=raw.get("replacement"),
        value=raw.get("value"),
        domain=raw.get("domain"),
        priority=raw.get("priority", 50),
        enabled=raw.get("enabled", True),
        created_at=raw.get("created_at", ""),
    )


def list_rules(directory: Path = RULES_DIR) -> list[Path]:
    if not directory.exists():
        return []
    paths = list(directory.glob("*.json"))
    def sort_key(p: Path):
        try:
            r = load_rule(p)
            return (r.priority, r.created_at)
        except Exception:
            return (999, "")
    return sorted(paths, key=sort_key)


def make_rule(
    name: str,
    scope: str,
    action: str,
    *,
    description: str | None = None,
    pattern: str | None = None,
    replacement: str | None = None,
    value: str | None = None,
    domain: str | None = None,
    priority: int = 50,
    enabled: bool = True,
) -> Rule:
    return Rule(
        id=str(uuid.uuid4()),
        name=name,
        scope=scope,
        action=action,
        description=description,
        pattern=pattern,
        replacement=replacement,
        value=value,
        domain=domain,
        priority=priority,
        enabled=enabled,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def save_html_cache(html: str, url: str = "") -> str:
    HTML_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = str(uuid.uuid4())
    path = HTML_CACHE_DIR / f"{key}.html.gz"
    path.write_bytes(gzip.compress(html.encode("utf-8", errors="replace")))
    return key


def load_html_cache(key: str) -> str | None:
    path = HTML_CACHE_DIR / f"{key}.html.gz"
    if not path.exists():
        return None
    return gzip.decompress(path.read_bytes()).decode("utf-8", errors="replace")



def save_pipeline_result(result: PipelineResult) -> Path:
    PIPELINE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = result.ran_at.replace(":", "-").replace("+", "").replace(".", "-")
    path = PIPELINE_RESULTS_DIR / f"{slug}.json"
    payload = dataclasses.asdict(result)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
