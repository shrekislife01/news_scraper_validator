from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Hibakategóriák alapértelmezett listája
# ---------------------------------------------------------------------------

class FieldError(str, Enum):
    MISSING           = "MISSING"           # Mező hiányzik / üres
    WRONG_CONTENT     = "WRONG_CONTENT"     # Helytelen tartalom
    PARTIAL_CONTENT   = "PARTIAL_CONTENT"   # Részleges / csonka tartalom
    FORMAT_ERROR      = "FORMAT_ERROR"      # Formátum hiba
    EXTRA_CONTENT     = "EXTRA_CONTENT"     # Felesleges tartalom (zaj)
    TRUNCATED         = "TRUNCATED"         # Szöveg le van vágva
    ENCODING_ERROR    = "ENCODING_ERROR"    # Kódolási hiba
    WRONG_AUTHOR      = "WRONG_AUTHOR"      # Rossz szerző neve
    MULTIPLE_AUTHORS  = "MULTIPLE_AUTHORS"  # Több szerző összekeverve
    WRONG_DATE        = "WRONG_DATE"        # Rossz dátum
    DATE_FORMAT_ERROR = "DATE_FORMAT_ERROR" # Dátum formátum hiba
    WRONG_KEYWORDS    = "WRONG_KEYWORDS"    # Helytelen kulcsszavak
    OTHER             = "OTHER"             # Egyéb hiba


FIELD_ERROR_LABELS: dict[str, str] = {
    FieldError.MISSING:           "Hiányzik",
    FieldError.WRONG_CONTENT:     "Helytelen tartalom",
    FieldError.PARTIAL_CONTENT:   "Részleges tartalom",
    FieldError.FORMAT_ERROR:      "Formátum hiba",
    FieldError.EXTRA_CONTENT:     "Felesleges tartalom (zaj)",
    FieldError.TRUNCATED:         "Csonkított szöveg",
    FieldError.ENCODING_ERROR:    "Kódolási hiba",
    FieldError.WRONG_AUTHOR:      "Rossz szerző",
    FieldError.MULTIPLE_AUTHORS:  "Több szerző összekeverve",
    FieldError.WRONG_DATE:        "Rossz dátum",
    FieldError.DATE_FORMAT_ERROR: "Dátum formátum hiba",
    FieldError.WRONG_KEYWORDS:    "Helytelen kulcsszavak",
    FieldError.OTHER:             "Egyéb",
}


# ---------------------------------------------------------------------------
# Adatmodellek
# ---------------------------------------------------------------------------

VALIDATED_FIELDS = ("title", "text", "author", "date", "keywords")


@dataclass
class FieldValidation:
    """Egy kinyert mező emberi értékelése."""

    field_name: str
    is_correct: bool | None = None       # None = nem értékelt; True = helyes; False = hibás
    error_category: str | None = None    # FieldError value vagy None
    corrected_value: str | None = None   # A helyes érték (ha hibás)
    comment: str | None = None           # Szabad szöveges megjegyzés


@dataclass
class ValidationResult:
    """Egy teljes kinyerési eredmény emberi validációja."""

    id: str                              # UUID4
    run: dict                            # dataclasses.asdict(TestRun)
    fields: dict[str, dict]             # field_name → asdict(FieldValidation)
    global_score: float | None           # 0–100, súlyozott átlag; None ha nincs értékelt mező
    overall_comment: str | None          # Összesített megjegyzés
    validated_at: str                    # ISO UTC timestamp
