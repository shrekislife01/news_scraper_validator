import sys
import os
import time
import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from src.extractor.extractor import NewsExtractor
from src.scraper.fetcher import fetch, FetchErrorCategory


class ExtractionStatus(str, Enum):
    SUCCESS = "success"  # minden fő mező kitöltve
    PARTIAL = "partial"  # lefutott, de van hiányzó mező
    FAILED  = "failed"   # fetch hiba VAGY extractor kivétel


@dataclass
class TestRun:
    url: str
    title: str | None = None
    text: str | None = None
    author: str | None = None
    date: str | None = None       #JSON-safe
    keywords: list[str] = field(default_factory=list)
    page: str | None = None
    status: ExtractionStatus = ExtractionStatus.FAILED
    error_category: str | None = None
    error_detail: str | None = None
    duration_ms: float | None = None
    ran_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def run_test(url: str, with_keywords: bool = True) -> TestRun:
    """
    Teljes tesztelési pipeline: URL validálás → HTML letöltés → kinyerés → TestRun visszaadás.
    Sosem dob kivételt.
    """
    url = (url or "").strip()
    start = time.perf_counter()

    def elapsed_ms():
        return round((time.perf_counter() - start) * 1000, 1)

    # 1. URL alapvalidálás
    if not url or not url.startswith(("http://", "https://")):
        return TestRun(
            url=url,
            status=ExtractionStatus.FAILED,
            error_category=FetchErrorCategory.INVALID_URL,
            error_detail="Az URL-nek http:// vagy https:// sémával kell kezdődnie.",
            duration_ms=elapsed_ms(),
        )

    # 2. HTML letöltés
    fetch_result = fetch(url)
    print("Fetched (?)")
    if fetch_result.error_category is not None:
        return TestRun(
            url=url,
            status=ExtractionStatus.FAILED,
            error_category=fetch_result.error_category,
            error_detail=fetch_result.error_detail,
            duration_ms=elapsed_ms(),
        )

    # 3. Kinyerés
    try:
        extractor = NewsExtractor(fetch_result.html, url)
        print("Extractor created")
        result = extractor.extract(with_kw=with_keywords)
    except Exception as e:
        return TestRun(
            url=url,
            status=ExtractionStatus.FAILED,
            error_category="PARSE_ERROR",
            error_detail=str(e),
            duration_ms=elapsed_ms(),
        )

    # 4. Dátum formázás (datetime → str)
    raw_date = result.get("date")
    date_str = str(raw_date) if raw_date is not None else None

    # 5. Státusz meghatározás
    main_fields = [result.get("title"), result.get("text"), result.get("author"), raw_date]
    filled = [f for f in main_fields if f]
    if len(filled) == len(main_fields):
        status = ExtractionStatus.SUCCESS
    elif filled:
        status = ExtractionStatus.PARTIAL
    else:
        status = ExtractionStatus.FAILED

    return TestRun(
        url=url,
        title=result.get("title") or None,
        text=result.get("text") or None,
        author=result.get("author") or None,
        date=date_str,
        keywords=result.get("keywords") or [],
        page=result.get("page") or None,
        status=status,
        error_category=None,
        error_detail=None,
        duration_ms=elapsed_ms(),
    )
