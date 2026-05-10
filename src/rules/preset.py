from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass
class RulePreset:
    id: str
    name: str
    created_at: str
    rules: list[dict] = field(default_factory=list)


def make_preset(name: str, rules: list) -> RulePreset:
    from src.rules.model import Rule
    import dataclasses

    rule_dicts = []
    for r in rules:
        if isinstance(r, Rule):
            rule_dicts.append(dataclasses.asdict(r))
        else:
            rule_dicts.append(r)

    return RulePreset(
        id=str(uuid.uuid4()),
        name=name,
        created_at=datetime.now(timezone.utc).isoformat(),
        rules=rule_dicts,
    )
