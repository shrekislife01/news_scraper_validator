from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from .applicators import apply_rule
from .model import PipelineResult, Rule, RuleApplication

if TYPE_CHECKING:
    from src.scraper.runner import TestRun


class RuleEngine:

    def __init__(self, rules: list[Rule]) -> None:
        self._rules: list[Rule] = sorted(
            [r for r in rules if r.enabled],
            key=lambda r: (r.priority, r.created_at),
        )

    @classmethod
    def from_directory(cls, path: Path | None = None) -> "RuleEngine":
        """Betölti az összes szabályt a rules/ könyvtárból."""
        from .storage import RULES_DIR, list_rules, load_rule

        directory = path or RULES_DIR
        rules: list[Rule] = []
        for p in list_rules(directory):
            try:
                rules.append(load_rule(p))
            except Exception:
                pass  # sérült JSON fájl: kihagyás
        return cls(rules)

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def get_css_overrides(self, domain: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for rule in self._rules:
            if rule.action != "CSS_SELECTOR_OVERRIDE":
                continue
            if rule.domain and rule.domain not in domain:
                continue
            if rule.pattern:
                result[rule.scope] = rule.pattern
        return result

    def apply(self, test_run: "TestRun") -> PipelineResult:
        original_dict = dataclasses.asdict(test_run)
        modified: dict = dict(original_dict)  # sima másolat — primitívek

        domain = test_run.page or ""
        applications: list[RuleApplication] = []

        for rule in self._rules:
            if rule.action == "CSS_SELECTOR_OVERRIDE":
                continue

            if rule.domain and rule.domain not in domain:
                continue

            field = rule.scope
            if field not in modified:
                continue

            original_value = modified[field]
            new_value, changed = apply_rule(rule, original_value)
            modified[field] = new_value

            applications.append(
                RuleApplication(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    scope=field,
                    original_value=original_value,
                    new_value=new_value,
                    changed=changed,
                )
            )

        return PipelineResult(
            original_run=original_dict,
            modified_run=modified,
            applied=[dataclasses.asdict(a) for a in applications],
            rules_ran=len(applications),
            rules_changed=sum(1 for a in applications if a.changed),
            ran_at=datetime.now(timezone.utc).isoformat(),
        )
