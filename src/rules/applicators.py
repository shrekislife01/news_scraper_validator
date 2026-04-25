from __future__ import annotations

import re
from typing import Any

from .model import Rule, RuleAction


def _regex_replace(rule: Rule, value: Any) -> Any:
    if not isinstance(value, str) or not rule.pattern:
        return value
    return re.sub(rule.pattern, rule.replacement or "", value)


def _strip_prefix(rule: Rule, value: Any) -> Any:
    if not isinstance(value, str) or not rule.value:
        return value
    if value.startswith(rule.value):
        return value[len(rule.value):]
    return value


def _strip_suffix(rule: Rule, value: Any) -> Any:
    if not isinstance(value, str) or not rule.value:
        return value
    if value.endswith(rule.value):
        return value[: -len(rule.value)]
    return value


def _set_null_if(rule: Rule, value: Any) -> Any:
    if not isinstance(value, str) or not rule.pattern:
        return value
    if re.search(rule.pattern, value):
        return None
    return value


def _normalize_ws(rule: Rule, value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return re.sub(r"\s+", " ", value).strip()


def _list_remove(rule: Rule, value: Any) -> Any:
    if not isinstance(value, list) or not rule.pattern:
        return value
    compiled = re.compile(rule.pattern, re.IGNORECASE)
    return [item for item in value if not compiled.search(str(item))]


_DISPATCH = {
    RuleAction.REGEX_REPLACE: _regex_replace,
    RuleAction.STRIP_PREFIX:  _strip_prefix,
    RuleAction.STRIP_SUFFIX:  _strip_suffix,
    RuleAction.SET_NULL_IF:   _set_null_if,
    RuleAction.NORMALIZE_WS:  _normalize_ws,
    RuleAction.LIST_REMOVE:   _list_remove,
}


def apply_rule(rule: Rule, value: Any) -> tuple[Any, bool]:
    handler = _DISPATCH.get(RuleAction(rule.action))
    if handler is None:
        return value, False
    new_value = handler(rule, value)
    return new_value, new_value != value
