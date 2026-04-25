"""
Automatikus szabályjavaslat-generátor.

Beolvassa az összes mentett validációs JSON fájlt, megkeresi azokat a
mezőket, amelyeket a felhasználó hibásnak jelölt és javított értéket adott
meg, majd mintát keres a (eredeti → javított) párok között.

Felismert stratégiák (prioritás szerinti sorrendben):
  1. NORMALIZE_WS  — ha szóköz-normalizálás adja a javított értéket
  2. STRIP_SUFFIX  — ha azonos literális utótag lett eltávolítva
  3. STRIP_PREFIX  — ha azonos literális előtag lett eltávolítva
  4. REGEX_REPLACE — ha az eltávolított rész különböző de azonos szerkezetű
                     (pl. mindig dátum, csak más számokkal → \\d+ általánosítás)
"""

from __future__ import annotations

import json
import re
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

try:
    from bs4 import BeautifulSoup as _BS
    _BS_AVAILABLE = True
except ImportError:
    _BS_AVAILABLE = False

from .storage import RULES_DIR, list_rules, load_rule, load_html_cache

VALIDATIONS_DIR = Path(__file__).parent.parent.parent / "validations"

_STRING_FIELDS = {"title", "text", "author", "date"}


@dataclass
class RuleSuggestion:
    """Egy automatikusan generált, még nem jóváhagyott szabályjavaslat."""

    id: str
    scope: str
    action: str
    pattern: str | None
    replacement: str | None
    value: str | None
    domain: str | None
    name: str
    description: str
    confidence: int
    examples: list[dict]


def analyze_validations(
    validations_dir: Path = VALIDATIONS_DIR,
    rules_dir: Path = RULES_DIR,
) -> list[RuleSuggestion]:

    grouped: dict[tuple, dict[str, list]] = defaultdict(lambda: defaultdict(list))

    for path in sorted(validations_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        run = data.get("run", {})
        domain: str | None = run.get("page") or None
        url: str = run.get("url", path.stem)
        fields: dict = data.get("fields", {})

        for field_name, field_data in fields.items():
            if field_data.get("is_correct") is not False:
                continue
            corrected = field_data.get("corrected_value")
            if corrected is None:
                continue
            original = run.get(field_name)
            if original is None or field_name not in _STRING_FIELDS:
                continue

            orig_str = str(original)
            corr_str = str(corrected)

            grouped[(field_name, domain)][url].append((orig_str, corr_str))
            if domain:
                grouped[(field_name, None)][url].append((orig_str, corr_str))

    existing: list = []
    for p in list_rules(rules_dir):
        try:
            existing.append(load_rule(p))
        except Exception:
            pass

    css_override_covered: set[tuple] = set()
    suggestions: list[RuleSuggestion] = []
    seen_sigs: set[tuple] = set()

    if _BS_AVAILABLE:
        for path in sorted(validations_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue

            html = _load_html_for_validation(data)
            if not html:
                continue

            soup = _BS(html, "html.parser")
            run = data.get("run", {})
            domain_val: str | None = run.get("page") or None
            url_val: str = run.get("url", path.stem)
            fields: dict = data.get("fields", {})

            for field_name, field_data in fields.items():
                if field_data.get("is_correct") is not False:
                    continue
                corrected = field_data.get("corrected_value")
                if not corrected or field_name not in _STRING_FIELDS:
                    continue
                selector = _find_css_selector(soup, str(corrected))
                if not selector:
                    continue

                sig = (field_name, "CSS_SELECTOR_OVERRIDE", None, selector, domain_val)
                if sig in seen_sigs:
                    continue
                original = run.get(field_name)
                pairs = [(str(original) if original else "", str(corrected))]
                s = _make_css_override(field_name, domain_val, selector, 1, pairs)
                if _is_duplicate(s, existing):
                    continue
                seen_sigs.add(sig)
                suggestions.append(s)
                css_override_covered.add((field_name, domain_val))


    for (scope, domain), url_map in grouped.items():
        if (scope, domain) in css_override_covered:
            continue
        s = _try_generate(scope, domain, url_map)
        if s is None:
            continue
        sig = (s.scope, s.action, s.value, s.pattern, s.domain)
        if sig in seen_sigs or _is_duplicate(s, existing):
            continue
        seen_sigs.add(sig)
        suggestions.append(s)

        suggestions.sort(key=lambda s: (
        0 if s.action == "CSS_SELECTOR_OVERRIDE" else 1,
        -s.confidence,
        0 if s.domain else 1,
    ))
    return suggestions


def _try_generate(scope: str, domain: str | None, url_map: dict) -> RuleSuggestion | None:
   
    pairs: list[tuple[str, str]] = []
    for url_pairs in url_map.values():
        if url_pairs:
            o, c = url_pairs[0]
            pairs.append((o.strip(), c.strip()))

    if not pairs:
        return None

    conf = len(url_map)

    ws_eligible = [(o, c) for o, c in pairs if o and c is not None]
    if ws_eligible and all(_normalize_ws(o) == c for o, c in ws_eligible):
        return _make(scope, domain, "NORMALIZE_WS", None, None, None, conf, pairs)

    suffix_pairs = [(o, c) for o, c in pairs if c and len(o) > len(c) and o.startswith(c)]
    if suffix_pairs:
        suffixes = [o[len(c):] for o, c in suffix_pairs]
        counter = Counter(suffixes)
        best_suffix, literal_count = counter.most_common(1)[0]

        if literal_count >= 2:
            return _make(scope, domain, "STRIP_SUFFIX", None, None, best_suffix, literal_count, suffix_pairs)

        skeletons = {_digit_skeleton(s) for s in suffixes}
        if len(skeletons) == 1 and _has_digits(best_suffix):
            pattern = _to_regex_pattern(best_suffix)
            return _make(scope, domain, "REGEX_REPLACE", pattern, "", None, len(suffix_pairs), suffix_pairs)

        if literal_count == 1 and len(suffix_pairs) == 1:
            return _make(scope, domain, "STRIP_SUFFIX", None, None, best_suffix, 1, suffix_pairs)

    prefix_pairs = [(o, c) for o, c in pairs if c and len(o) > len(c) and o.endswith(c)]
    if prefix_pairs:
        prefixes = [o[: -len(c)] for o, c in prefix_pairs]
        counter = Counter(prefixes)
        best_prefix, literal_count = counter.most_common(1)[0]

        if literal_count >= 2:
            return _make(scope, domain, "STRIP_PREFIX", None, None, best_prefix, literal_count, prefix_pairs)

        skeletons = {_digit_skeleton(p) for p in prefixes}
        if len(skeletons) == 1 and _has_digits(best_prefix):
            pattern = "^" + _to_regex_pattern(best_prefix).rstrip("$")
            return _make(scope, domain, "REGEX_REPLACE", pattern, "", None, len(prefix_pairs), prefix_pairs)

        if literal_count == 1 and len(prefix_pairs) == 1:
            return _make(scope, domain, "STRIP_PREFIX", None, None, best_prefix, 1, prefix_pairs)

    return None


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _digit_skeleton(s: str) -> str:
    return re.sub(r"\d+", "D", s)


def _has_digits(s: str) -> bool:
    return bool(re.search(r"\d", s))


def _to_regex_pattern(s: str) -> str:
    parts = re.split(r"(\d+)", s)
    result = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            result.append(r"\d+")
        else:
            result.append(re.escape(part))
    return "".join(result) + "$"


def _make(scope, domain, action, pattern, replacement, value, confidence, pairs) -> RuleSuggestion:
    examples = [{"original": o, "corrected": c} for o, c in pairs[:3]]
    domain_tag = f" ({domain})" if domain else ""

    if action == "NORMALIZE_WS":
        name = f"Szóköz normalizálás — {scope}{domain_tag}"
        desc = f"Többszörös szóközöket egyre csökkenti és trimmel a {scope} mezőben."
    elif action == "STRIP_SUFFIX":
        short = (value or "")[:40]
        name = f"Utótag törlés — {scope}: \"{short}\"{domain_tag}"
        desc = f"Eltávolítja a \"{value}\" utótagot a {scope} mezőből."
    elif action == "STRIP_PREFIX":
        short = (value or "")[:40]
        name = f"Előtag törlés — {scope}: \"{short}\"{domain_tag}"
        desc = f"Eltávolítja a \"{value}\" előtagot a {scope} mezőből."
    else:  # REGEX_REPLACE
        short = (pattern or "")[:50]
        name = f"Regex csere — {scope}{domain_tag}"
        desc = f"Regex: {short} → \"{replacement}\""

    return RuleSuggestion(
        id=str(uuid.uuid4()),
        scope=scope,
        action=action,
        pattern=pattern,
        replacement=replacement,
        value=value,
        domain=domain,
        name=name,
        description=desc,
        confidence=confidence,
        examples=examples,
    )


def _load_html_for_validation(data: dict) -> str | None:
    key = data.get("html_cache_key")
    if not key:
        return None
    return load_html_cache(key)


def _find_css_selector(soup, correct_value: str) -> str | None:
    
    if not correct_value:
        return None
    for text_node in soup.find_all(string=lambda t: t and correct_value in t):
        tag = text_node.parent
        sel = _build_stable_selector(tag)
        if sel:
            return sel
    return None


def _build_stable_selector(tag) -> str | None:
    if tag is None:
        return None
    if tag.get("id"):
        return f"#{tag['id']}"
    classes = [c for c in (tag.get("class") or []) if not all(ch.isdigit() for ch in c)]
    if classes:
        return f"{tag.name}.{'.'.join(classes[:2])}"
    parent = tag.parent
    if parent and parent.get("class"):
        pc = [c for c in parent["class"] if not all(ch.isdigit() for ch in c)]
        if pc:
            return f".{pc[0]} > {tag.name}"
    return None


def _make_css_override(
    scope: str, domain: str | None, selector: str, confidence: int, pairs: list
) -> RuleSuggestion:
    domain_tag = f" ({domain})" if domain else ""
    return RuleSuggestion(
        id=str(uuid.uuid4()),
        scope=scope,
        action="CSS_SELECTOR_OVERRIDE",
        pattern=selector,
        replacement=None,
        value=None,
        domain=domain,
        name=f"CSS Override — {scope}{domain_tag}: {selector[:50]}",
        description=f"Közvetlenül a '{selector}' elemből veszi a {scope} értékét.",
        confidence=confidence,
        examples=[{"original": o, "corrected": c} for o, c in pairs[:3]],
    )


def _is_duplicate(s: RuleSuggestion, existing_rules: list) -> bool:
    for r in existing_rules:
        if (r.scope == s.scope
                and r.action == s.action
                and r.value == s.value
                and r.pattern == s.pattern
                and (r.domain == s.domain or r.domain is None)):
            return True
    return False
