from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuleScope(str, Enum):
    TITLE    = "title"
    TEXT     = "text"
    AUTHOR   = "author"
    DATE     = "date"
    KEYWORDS = "keywords"


class RuleAction(str, Enum):
    REGEX_REPLACE        = "REGEX_REPLACE"
    STRIP_PREFIX         = "STRIP_PREFIX"
    STRIP_SUFFIX         = "STRIP_SUFFIX"
    SET_NULL_IF          = "SET_NULL_IF"
    NORMALIZE_WS         = "NORMALIZE_WS"
    LIST_REMOVE          = "LIST_REMOVE"
    CSS_SELECTOR_OVERRIDE = "CSS_SELECTOR_OVERRIDE"


@dataclass
class Rule:
    """Egyetlen post-processing szabály leírása."""

    id: str
    name: str
    scope: str
    action: str
    description: str | None = None
    pattern: str | None = None
    replacement: str | None = None
    value: str | None = None
    domain: str | None = None
    priority: int = 50
    enabled: bool = True
    created_at: str = ""


@dataclass
class RuleApplication:

    rule_id: str
    rule_name: str
    scope: str
    original_value: Any
    new_value: Any
    changed: bool


@dataclass
class PipelineResult:

    original_run: dict
    modified_run: dict
    applied: list[dict]
    rules_ran: int
    rules_changed: int
    ran_at: str
    html_cache_key: str | None = None
    extraction_trace: dict | None = None
