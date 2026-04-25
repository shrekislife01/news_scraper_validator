from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FieldError(str, Enum):
    MISSING           = "MISSING"           # Field is missing / empty
    WRONG_CONTENT     = "WRONG_CONTENT"     # Incorrect content
    PARTIAL_CONTENT   = "PARTIAL_CONTENT"   # Partial / incomplete content
    FORMAT_ERROR      = "FORMAT_ERROR"      # Format error
    EXTRA_CONTENT     = "EXTRA_CONTENT"     # Extraneous content (noise)
    TRUNCATED         = "TRUNCATED"         # Text is cut off
    ENCODING_ERROR    = "ENCODING_ERROR"    # Encoding error
    WRONG_AUTHOR      = "WRONG_AUTHOR"      # Wrong author name
    MULTIPLE_AUTHORS  = "MULTIPLE_AUTHORS"  # Multiple authors mixed together
    WRONG_DATE        = "WRONG_DATE"        # Wrong date
    DATE_FORMAT_ERROR = "DATE_FORMAT_ERROR" # Date format error
    WRONG_KEYWORDS    = "WRONG_KEYWORDS"    # Incorrect keywords
    OTHER             = "OTHER"             # Other error


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



VALIDATED_FIELDS = ("title", "text", "author", "date", "keywords")


@dataclass
class FieldValidation:

    field_name: str
    is_correct: bool | None = None
    corrected_value: str | None = None
    comment: str | None = None


@dataclass
class ValidationResult:

    id: str
    run: dict
    fields: dict[str, dict]
    global_score: float | None
    overall_comment: str | None
    validated_at: str
    html_cache_key: str | None = None
    extraction_trace: dict | None = None
