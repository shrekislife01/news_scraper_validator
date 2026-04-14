from __future__ import annotations

from .model import FieldValidation

# ---------------------------------------------------------------------------
# Mezőnkénti súlyok (összegük 100)
# ---------------------------------------------------------------------------

FIELD_WEIGHTS: dict[str, int] = {
    "title":    25,
    "text":     35,
    "author":   20,
    "date":     15,
    "keywords":  5,
}


def compute_score(field_validations: dict[str, FieldValidation]) -> float | None:
    """
    Súlyozott pontszámot számít a validált mezők alapján.

    Csak az értékelt mezőket veszi figyelembe (is_correct is not None).
    Ha egyetlen mező sincs értékelve, None-t ad vissza.

    Returns:
        0–100 közötti float, vagy None.
    """
    correct_weight = 0
    total_weight = 0

    for field_name, fv in field_validations.items():
        if fv.is_correct is None:
            continue
        weight = FIELD_WEIGHTS.get(field_name, 0)
        total_weight += weight
        if fv.is_correct:
            correct_weight += weight

    if total_weight == 0:
        return None

    return round(correct_weight / total_weight * 100, 1)
