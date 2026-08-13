"""Day2 helpers: parse App Store URLs and collect US reviews."""

from __future__ import annotations

import csv
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Literal
import httpx

from app.models.schemas import Review
from app.services.url_parser import InvalidAppUrlError, extract_app_id

# backend/app/services/collect.py -> parents: services, app, backend, repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLES_DIR = REPO_ROOT / "data" / "samples"
IMPORTS_DIR = REPO_ROOT / "data" / "imports"

USER_AGENT = (
    "AppReviewPlanner/0.2 (+local assessment; respectful rate limits; "
    "iTunes/12.12.9 compatible)"
)
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/xml,application/json,text/xml,*/*",
}

ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "im": "http://itunes.apple.com/rss",
}


class CollectError(Exception):
    """Raised when review collection fails in a user-visible way."""


def sample_path(app_id: str) -> Path:
    return SAMPLES_DIR / f"{app_id}_us_reviews.json"


def _label(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return (node.text or "").strip()


def _parse_rss_xml(content: str, app_id: str, source: Literal["live", "sample", "import"]) -> list[Review]:
    root = ET.fromstring(content)
    entries = root.findall("atom:entry", ATOM_NS)
    reviews: list[Review] = []

    for entry in entries:
        # App metadata entry has im:name and no im:rating
        rating_node = entry.find("im:rating", ATOM_NS)
        if rating_node is None:
            continue

        entry_id = _label(entry.find("atom:id", ATOM_NS))
        review_id_match = re.search(r"/id(\d+)\b", entry_id) or re.search(r"(\d+)$", entry_id)
        review_id = review_id_match.group(1) if review_id_match else entry_id or f"rss-{len(reviews)+1}"

        author = entry.find("atom:author/atom:name", ATOM_NS)
        content_node = entry.find("atom:content", ATOM_NS)
        content = _label(content_node)
        # Sometimes content has HTML
        content = re.sub(r"<[^>]+>", " ", content)
        content = re.sub(r"\s+", " ", content).strip()

        rating_raw = _label(rating_node)
        rating = int(rating_raw) if rating_raw.isdigit() else None

        reviews.append(
            Review(
                id=str(review_id),
                app_id=app_id,
                rating=rating,
                title=_label(entry.find("atom:title", ATOM_NS)),
                content=content,
                author=_label(author),
                date=_label(entry.find("atom:updated", ATOM_NS)),
                version=_label(entry.find("im:version", ATOM_NS)),
                country="us",
                source=source,
            )
        )
    return reviews


def _fetch_rss_page(client: httpx.Client, app_id: str, page: int) -> list[Review]:
    url = (
        f"https://itunes.apple.com/us/rss/customerreviews/page={page}/"
        f"id={app_id}/sortby=mostrecent/xml"
    )
    response = client.get(url, headers=REQUEST_HEADERS, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return _parse_rss_xml(response.text, app_id, source="live")


def _strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _parse_mzstore_xml(content: str, app_id: str) -> list[Review]:
    """
    Fallback parser for iTunes MZStore review document XML.
    Used when the public RSS feed returns an empty entry list.
    """
    review_ids = re.findall(r"userReviewId=(\d+)", content)
    # Preserve order, unique
    ordered_ids: list[str] = []
    seen: set[str] = set()
    for rid in review_ids:
        if rid not in seen:
            seen.add(rid)
            ordered_ids.append(rid)

    ratings = [int(x) for x in re.findall(r'alt="([1-5]) stars"', content)]
    metas = re.findall(
        r"by\s*<GotoURL[^>]*>\s*<b>\s*([^<]+?)\s*</b>\s*</GotoURL>\s*-\s*Version\s*([^<\-]+?)\s*-\s*([^<]+?)\s*</SetFontStyle>",
        content,
        flags=re.S,
    )
    bodies = []
    for match in re.finditer(
        r'<TextView[^>]*styleSet="normal11"[^>]*>\s*<SetFontStyle[^>]*>([\s\S]*?)</SetFontStyle>',
        content,
    ):
        body = _strip_tags(match.group(1))
        if len(body) >= 5:
            bodies.append(body)

    # Titles often appear as bold text near the star row; best-effort extraction.
    titles = re.findall(
        r'<TextView[^>]*styleSet="basic15"[^>]*>\s*<SetFontStyle[^>]*>\s*<b>\s*([^<]+?)\s*</b>',
        content,
        flags=re.S,
    )
    if not titles:
        titles = re.findall(
            r'<TextView[^>]*maxLines="1"[^>]*>\s*<SetFontStyle[^>]*>\s*<b>\s*([^<]+?)\s*</b>',
            content,
            flags=re.S,
        )
        # Filter out UI chrome
        titles = [t.strip() for t in titles if t.strip().lower() not in {"report a concern"}]

    count = min(len(ordered_ids), len(ratings), len(metas), len(bodies))
    reviews: list[Review] = []
    for i in range(count):
        author, version, date = metas[i]
        title = titles[i].strip() if i < len(titles) else ""
        reviews.append(
            Review(
                id=ordered_ids[i],
                app_id=app_id,
                rating=ratings[i],
                title=title,
                content=bodies[i],
                author=author.strip(),
                date=date.strip(),
                version=version.strip(),
                country="us",
                source="live",
            )
        )
    return reviews


def _fetch_mzstore_page(client: httpx.Client, app_id: str, page_number: int) -> list[Review]:
    url = (
        "https://itunes.apple.com/WebObjects/MZStore.woa/wa/viewContentsUserReviews"
        f"?id={app_id}&pageNumber={page_number}&sortOrdering=4"
        "&onlyLatestVersion=false&type=Purple+Software"
    )
    response = client.get(url, headers=REQUEST_HEADERS, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return _parse_mzstore_xml(response.text, app_id)


def fetch_reviews_live(
    app_id: str,
    country: str = "us",
    max_pages: int = 5,
    page_delay_sec: float = 0.8,
) -> tuple[list[Review], dict[str, Any]]:
    if country.lower() != "us":
        raise CollectError("This assessment requires US storefront reviews (country=us).")

    reviews: list[Review] = []
    method = "rss_xml"
    limitations: list[str] = [
        "Public feeds may not include the full historical review corpus.",
        "Ordering is most recent first.",
        "Request pacing is applied to reduce load on Apple endpoints.",
    ]

    with httpx.Client() as client:
        # 1) Prefer public RSS XML (not HTML scraping)
        for page in range(1, max_pages + 1):
            try:
                page_reviews = _fetch_rss_page(client, app_id, page)
            except Exception as exc:  # noqa: BLE001
                if page == 1:
                    break
                limitations.append(f"RSS page {page} failed: {exc}")
                break

            if not page_reviews:
                break

            reviews.extend(page_reviews)
            time.sleep(page_delay_sec)

        # 2) Fallback for apps where RSS returns an empty feed
        if not reviews:
            method = "mzstore_viewContentsUserReviews"
            limitations.append(
                "RSS feed returned no entries for this app; fell back to "
                "iTunes MZStore viewContentsUserReviews document endpoint."
            )
            for page_number in range(0, max_pages):
                try:
                    page_reviews = _fetch_mzstore_page(client, app_id, page_number)
                except Exception as exc:  # noqa: BLE001
                    if page_number == 0:
                        raise CollectError(f"Live collection failed: {exc}") from exc
                    limitations.append(f"MZStore page {page_number} failed: {exc}")
                    break

                if not page_reviews:
                    break

                # Deduplicate by id across pages
                existing = {r.id for r in reviews}
                reviews.extend([r for r in page_reviews if r.id not in existing])
                time.sleep(page_delay_sec)

    if not reviews:
        raise CollectError(
            f"No US reviews found for app_id={app_id}. "
            "Try source=sample/import, or verify network access."
        )

    # Stable dedupe
    deduped: list[Review] = []
    seen_ids: set[str] = set()
    for review in reviews:
        if review.id in seen_ids:
            continue
        seen_ids.add(review.id)
        deduped.append(review)

    meta = {
        "source": "live",
        "method": method,
        "storefront": "us",
        "app_id": app_id,
        "count": len(deduped),
        "max_pages": max_pages,
        "limitations": limitations,
        "cached": False,
    }
    return deduped, meta


def reviews_to_dicts(reviews: list[Review]) -> list[dict[str, Any]]:
    return [r.model_dump() for r in reviews]


def save_sample(app_id: str, reviews: list[Review], meta: dict[str, Any] | None = None) -> Path:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    path = sample_path(app_id)
    payload = {
        "cached": True,
        "storefront": "us",
        "app_id": app_id,
        "note": "Cached sample for offline demo. Prefer live collection when network is available.",
        "collection_meta": meta or {},
        "reviews": reviews_to_dicts(reviews),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_sample(app_id: str) -> tuple[list[Review], dict[str, Any]]:
    path = sample_path(app_id)
    if not path.exists():
        raise CollectError(
            f"No cached sample found at {path}. Run live collection once to create it, "
            "or place a sample JSON file there."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    reviews = [Review.model_validate(item) for item in payload.get("reviews", [])]
    for review in reviews:
        review.source = "sample"
        review.country = "us"
        review.app_id = app_id
    meta = {
        "source": "sample",
        "storefront": payload.get("storefront", "us"),
        "app_id": app_id,
        "count": len(reviews),
        "cached": True,
        "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "note": payload.get("note"),
        "limitations": [
            "Using cached sample data labeled for offline review.",
            "Cached results do not replace live collection when network is available.",
        ],
        "original_collection_meta": payload.get("collection_meta", {}),
    }
    if not reviews:
        raise CollectError(f"Cached sample at {path} contains zero reviews.")
    return reviews, meta


def _normalize_import_item(item: dict[str, Any], app_id: str) -> Review:
    review_id = str(item.get("id") or item.get("review_id") or "").strip()
    if not review_id:
        raise CollectError("Imported review is missing id/review_id")

    rating_raw = item.get("rating")
    rating = int(rating_raw) if rating_raw not in (None, "") else None

    return Review(
        id=review_id,
        app_id=str(item.get("app_id") or app_id),
        rating=rating,
        title=str(item.get("title") or ""),
        content=str(item.get("content") or item.get("body") or ""),
        author=str(item.get("author") or item.get("user") or ""),
        date=(str(item["date"]) if item.get("date") not in (None, "") else None),
        version=(str(item["version"]) if item.get("version") not in (None, "") else None),
        country=str(item.get("country") or "us"),
        source="import",
    )


def load_reviews_from_json(file_path: str | Path, app_id: str | None = None) -> tuple[list[Review], dict[str, Any]]:
    path = Path(file_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise CollectError(f"Import JSON not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "reviews" in payload:
        items = payload["reviews"]
        app_id = str(payload.get("app_id") or app_id or "unknown")
    elif isinstance(payload, list):
        items = payload
        app_id = str(app_id or "unknown")
    else:
        raise CollectError("JSON import must be a list of reviews or an object with reviews[]")

    reviews = [_normalize_import_item(item, app_id) for item in items]
    meta = {
        "source": "import",
        "format": "json",
        "path": str(path),
        "app_id": app_id,
        "count": len(reviews),
        "cached": False,
        "storefront": "us",
        "limitations": ["Imported dataset trust depends on the provider."],
    }
    return reviews, meta


def load_reviews_from_csv(file_path: str | Path, app_id: str | None = None) -> tuple[list[Review], dict[str, Any]]:
    path = Path(file_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise CollectError(f"Import CSV not found: {path}")

    app_id = str(app_id or "unknown")
    reviews: list[Review] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            reviews.append(_normalize_import_item(row, app_id))

    meta = {
        "source": "import",
        "format": "csv",
        "path": str(path),
        "app_id": app_id,
        "count": len(reviews),
        "cached": False,
        "storefront": "us",
        "limitations": [
            "CSV columns expected: id,rating,title,content (optional: author,date,version,app_id,country)."
        ],
    }
    return reviews, meta


def collect_reviews(
    app_url: str,
    source: Literal["live", "sample", "import"] = "live",
    import_path: str | None = None,
    max_pages: int = 5,
    refresh_sample_on_live: bool = True,
) -> dict[str, Any]:
    try:
        app_id = extract_app_id(app_url)
    except InvalidAppUrlError as exc:
        raise CollectError(str(exc)) from exc

    if source == "live":
        reviews, meta = fetch_reviews_live(app_id, country="us", max_pages=max_pages)
        if refresh_sample_on_live:
            sample_file = save_sample(app_id, reviews, meta)
            meta["sample_saved_to"] = str(sample_file.relative_to(REPO_ROOT)).replace("\\", "/")
    elif source == "sample":
        reviews, meta = load_sample(app_id)
    elif source == "import":
        if not import_path:
            raise CollectError("source=import requires import_path")
        suffix = Path(import_path).suffix.lower()
        if suffix == ".json":
            reviews, meta = load_reviews_from_json(import_path, app_id=app_id)
        elif suffix == ".csv":
            reviews, meta = load_reviews_from_csv(import_path, app_id=app_id)
        else:
            raise CollectError("import_path must end with .json or .csv")
    else:
        raise CollectError(f"Unsupported source: {source}")

    return {
        "app_id": app_id,
        "reviews": reviews_to_dicts(reviews),
        "collection_meta": meta,
    }
