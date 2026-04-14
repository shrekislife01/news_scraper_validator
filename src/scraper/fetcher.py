import requests
from dataclasses import dataclass
from enum import Enum

REQUEST_TIMEOUT = 10          # seconds
MAX_CONTENT_LENGTH = 5_000_000  # 5 MB


class FetchErrorCategory(str, Enum):
    TIMEOUT     = "TIMEOUT"
    HTTP_ERROR  = "HTTP_ERROR"
    CONNECTION  = "CONNECTION"
    TOO_LARGE   = "TOO_LARGE"
    INVALID_URL = "INVALID_URL"
    UNKNOWN     = "UNKNOWN"


@dataclass
class FetchResult:
    html: str | None
    error_category: FetchErrorCategory | None  # None = siker
    error_detail: str | None
    status_code: int | None


def fetch(url: str, timeout: int = REQUEST_TIMEOUT) -> FetchResult:
    """Letölti az URL HTML tartalmát. Mindig FetchResult-ot ad vissza, sosem dob kivételt."""
    if not url or not url.startswith(("http://", "https://")):
        return FetchResult(
            html=None,
            error_category=FetchErrorCategory.INVALID_URL,
            error_detail="Az URL-nek http:// vagy https:// sémával kell kezdődnie.",
            status_code=None,
        )

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NewsScraperValidator/1.0)"},
            stream=True,
        )

        print("Got to response")

        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_CONTENT_LENGTH:
            return FetchResult(
                html=None,
                error_category=FetchErrorCategory.TOO_LARGE,
                error_detail=f"Az oldal mérete meghaladja az 5 MB-os korlátot ({int(content_length):,} bájt).",
                status_code=response.status_code,
            )

        content = bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            if chunk:
                content.extend(chunk)
                if len(content) > MAX_CONTENT_LENGTH:
                    return FetchResult(
                        html=None,
                        error_category=FetchErrorCategory.TOO_LARGE,
                        error_detail="Az oldal mérete meghaladja az 5 MB-os korlátot.",
                        status_code=response.status_code,
                    )

        print("Done chunking")

        if response.status_code >= 400:
            return FetchResult(
                html=None,
                error_category=FetchErrorCategory.HTTP_ERROR,
                error_detail=f"HTTP {response.status_code} hiba.",
                status_code=response.status_code,
            )

        raw_bytes = bytes(content)
        encoding = response.encoding or "utf-8"
        html = raw_bytes.decode(encoding, errors="replace")

        print("Decoded")
        return FetchResult(
            html=html,
            error_category=None,
            error_detail=None,
            status_code=response.status_code,
        )

    except requests.exceptions.Timeout:
        return FetchResult(
            html=None,
            error_category=FetchErrorCategory.TIMEOUT,
            error_detail=f"A lekérés túllépte a {timeout} másodperces időkorlátot.",
            status_code=None,
        )
    except requests.exceptions.ConnectionError as e:
        return FetchResult(
            html=None,
            error_category=FetchErrorCategory.CONNECTION,
            error_detail=f"Nem sikerült csatlakozni: {e}",
            status_code=None,
        )
    except Exception as e:
        return FetchResult(
            html=None,
            error_category=FetchErrorCategory.UNKNOWN,
            error_detail=str(e),
            status_code=None,
        )
