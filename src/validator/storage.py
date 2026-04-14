from __future__ import annotations

import dataclasses
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .model import FieldValidation, ValidationResult

VALIDATIONS_DIR = Path(__file__).parent.parent.parent / "validations"


def save_validation(result: ValidationResult) -> Path:
    """
    ValidationResult-et ment JSON fájlba a validations/ könyvtárba.

    Könyvtárat létrehozza, ha még nem létezik.
    Visszaadja a létrehozott fájl elérési útját.
    """
    VALIDATIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = VALIDATIONS_DIR / f"{result.id}.json"
    payload = dataclasses.asdict(result)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_validation(path: Path) -> ValidationResult:
    """
    JSON fájlból visszatölti a ValidationResult-et.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))

    # Rekonstruáljuk a FieldValidation dict-eket
    fields: dict[str, dict] = raw.get("fields", {})

    return ValidationResult(
        id=raw["id"],
        run=raw["run"],
        fields=fields,
        global_score=raw.get("global_score"),
        overall_comment=raw.get("overall_comment"),
        validated_at=raw["validated_at"],
    )


def list_validations() -> list[Path]:
    """
    Visszaadja a validations/ könyvtárban lévő JSON fájlok listáját,
    legújabbtól a legrégebbiig rendezve (módosítási idő alapján).
    """
    if not VALIDATIONS_DIR.exists():
        return []
    return sorted(
        VALIDATIONS_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def build_validation_result(
    run_dict: dict,
    field_data: dict[str, dict],
    global_score: float | None,
    overall_comment: str | None,
) -> ValidationResult:
    """
    Segédfüggvény: a UI callback-ekből érkező nyers adatokból ValidationResult-et épít.

    Args:
        run_dict:        dataclasses.asdict(TestRun) – a tárolt kinyerési eredmény
        field_data:      {field_name: {"is_correct": bool|None, "error_category": str|None,
                          "corrected_value": str|None, "comment": str|None}}
        global_score:    compute_score() eredménye
        overall_comment: összesített megjegyzés
    """
    return ValidationResult(
        id=str(uuid.uuid4()),
        run=run_dict,
        fields=field_data,
        global_score=global_score,
        overall_comment=overall_comment or None,
        validated_at=datetime.now(timezone.utc).isoformat(),
    )
