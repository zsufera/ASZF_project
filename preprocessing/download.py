from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen

import yaml


DEFAULT_CONFIG_PATH = Path("config/doc_sources.yaml")
DEFAULT_OUTPUT_DIR = Path("data/raw_pdfs")
DEFAULT_REPORT_PATH = Path("data/raw_pdfs/download_metadata.json")
PDF_LINK_PATTERN = re.compile(r"""(?P<url>https?://[^"' <>)]+?\.pdf|/[^"' <>)]+?\.pdf)""", re.IGNORECASE)
HREF_PATTERN = re.compile(r"""(?:href|src)=["'](?P<url>[^"']+?\.pdf(?:\?[^"']*)?)["']""", re.IGNORECASE)


@dataclass
class DownloadedDocument:
    file_name: str
    local_path: str
    source_url: str
    source_page: str
    szolgaltato: str
    dok_tipus: str
    downloaded_at: str
    size_bytes: int


@dataclass
class DownloadError:
    url: str
    source_page: str
    reason: str


def load_doc_sources(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing doc source config: {config_path}")
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def fetch_bytes(url: str, timeout: int = 45) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
            ),
            "Accept": "text/html,application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_text(url: str) -> str:
    content = fetch_bytes(url)
    return content.decode("utf-8", errors="ignore")


def extract_pdf_links(html: str, base_url: str) -> list[str]:
    links: set[str] = set()
    for pattern in (HREF_PATTERN, PDF_LINK_PATTERN):
        for match in pattern.finditer(html):
            links.add(urljoin(base_url, match.group("url")))
    return sorted(links)


def infer_provider_from_page(source_page: str) -> str:
    lowered = source_page.lower()
    if "invitech" in lowered:
        return "Invitech"
    if "ah-media" in lowered or "ah_media" in lowered:
        return "AH Media"
    if "helyi-kabeles" in lowered or "helyi_kabeles" in lowered:
        return "helyi_kabeles"
    return "ONE"


def infer_doc_type_from_url(url: str) -> str:
    lowered = unquote(url.lower())
    if "melleklet" in lowered or "melléklet" in lowered:
        return "melléklet"
    if "egyeb" in lowered or "egyéb" in lowered or "felhasznalasi" in lowered:
        return "Egyéb felhasználási feltételek"
    return "ÁSZF"


def sanitize_filename(file_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", unquote(file_name))
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_name).strip("._")
    if not ascii_name.lower().endswith(".pdf"):
        ascii_name = f"{ascii_name}.pdf"
    return ascii_name or "document.pdf"


def filename_from_url(url: str, prefix: str | None = None) -> str:
    parsed = urlparse(url)
    base_name = sanitize_filename(Path(parsed.path).name or "document.pdf")
    return f"{prefix}_{base_name}" if prefix else base_name


def discover_pdf_links(source_pages: list[str], manual_pdf_urls: list[str]) -> dict[str, str]:
    discovered: dict[str, str] = {}
    for page in source_pages:
        try:
            html = fetch_text(page)
        except Exception as exc:
            print(f"WARNING: failed to fetch source page {page}: {exc}")
            continue
        for pdf_url in extract_pdf_links(html, page):
            discovered[pdf_url] = page
    for pdf_url in manual_pdf_urls:
        discovered[pdf_url] = "manual_pdf_urls"
    return discovered


def download_pdfs(
    config_path: Path = DEFAULT_CONFIG_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[list[DownloadedDocument], list[DownloadError]]:
    config = load_doc_sources(config_path)
    source_pages = list(config.get("source_pages", []))
    manual_pdf_urls = list(config.get("manual_pdf_urls", []))
    output_dir.mkdir(parents=True, exist_ok=True)
    discovered = discover_pdf_links(source_pages, manual_pdf_urls)
    downloaded_at = datetime.now(timezone.utc).isoformat()
    downloaded: list[DownloadedDocument] = []
    errors: list[DownloadError] = []

    for index, (pdf_url, source_page) in enumerate(sorted(discovered.items()), start=1):
        provider = infer_provider_from_page(source_page)
        file_name = filename_from_url(pdf_url, prefix=f"{index:03d}_{provider.replace(' ', '_')}")
        target_path = output_dir / file_name
        try:
            content = fetch_bytes(pdf_url)
        except Exception as exc:
            reason = f"failed to download PDF: {exc}"
            errors.append(DownloadError(url=pdf_url, source_page=source_page, reason=reason))
            print(f"WARNING: {reason} ({pdf_url})")
            continue
        if not content.startswith(b"%PDF"):
            reason = "skipped non-PDF response"
            errors.append(DownloadError(url=pdf_url, source_page=source_page, reason=reason))
            print(f"WARNING: {reason} from {pdf_url}")
            continue
        target_path.write_bytes(content)
        downloaded.append(
            DownloadedDocument(
                file_name=file_name,
                local_path=target_path.as_posix(),
                source_url=pdf_url,
                source_page=source_page,
                szolgaltato=provider,
                dok_tipus=infer_doc_type_from_url(pdf_url),
                downloaded_at=downloaded_at,
                size_bytes=len(content),
            )
        )
        print(f"Downloaded: {target_path}")

    return downloaded, errors


def write_download_report(
    items: list[DownloadedDocument],
    errors: list[DownloadError],
    report_path: Path = DEFAULT_REPORT_PATH,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(items),
        "documents": [asdict(item) for item in items],
        "error_count": len(errors),
        "errors": [asdict(error) for error in errors],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download ONE ASZF PDF documents.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    items, errors = download_pdfs(config_path=Path(args.config), output_dir=Path(args.output_dir))
    write_download_report(items, errors, Path(args.report))
    print(f"Downloaded {len(items)} PDF document(s). Report: {args.report}")


if __name__ == "__main__":
    main()
