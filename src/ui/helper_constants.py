from src.validator import (
    FieldError,
    FIELD_ERROR_LABELS
)

# ---------------------------------------------------------------------------
# Segédadatok a validációs dropdownhoz
# ---------------------------------------------------------------------------

ERROR_OPTIONS = [
    {"label": FIELD_ERROR_LABELS[e], "value": e.value}
    for e in FieldError
]

FIELD_LABELS = {
    "title":    "Cím",
    "text":     "Szöveg",
    "author":   "Szerző",
    "date":     "Dátum",
    "keywords": "Kulcsszavak",
}

RADIO_OPTIONS = [
    {"label": "Nem értékelt", "value": "none"},
    {"label": "Helyes",       "value": "correct"},
    {"label": "Hibás",        "value": "incorrect"},
]