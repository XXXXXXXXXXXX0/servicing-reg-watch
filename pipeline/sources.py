"""HTTP clients. LiveClient talks to the Federal Register and eCFR APIs;
FixtureClient answers the same calls from fixtures/ with no network access."""
from __future__ import annotations

import html
import json
import math
import os
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from . import config
from .common import FIXTURES_DIR


class NotFound(Exception):
    pass


class Blocked(Exception):
    """The Federal Register redirected to its bot wall (unblock.federalregister.gov)."""


class TextUnavailable(Exception):
    """Full text could not be fetched; the message is the logged reason."""


def govinfo_urls(doc: dict) -> dict[str, str]:
    """GovInfo locations of a Federal Register document's HTML text."""
    package = f"FR-{doc['publication_date']}"
    num = doc["document_number"]
    return {
        "api": f"{config.GOVINFO_API}/packages/{package}/granules/{num}/htm",
        "www": f"{config.GOVINFO_WWW}/content/pkg/{package}/html/{num}.htm",
    }


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(markup: str) -> str:
    """Strip tags (and script/style content) and decode entities. GovInfo FR
    granules are a <pre> block, so the text keeps its own line breaks."""
    p = _TextExtractor()
    p.feed(markup)
    p.close()
    return html.unescape("".join(p.parts)).strip() + "\n"


class LiveClient:
    offline = False

    def __init__(self, retries: int = 4, timeout: int = 60):
        import requests  # imported lazily so offline runs never need it

        self._requests = requests
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "servicing-reg-watch/1 (regulatory change monitoring)"
        # eCFR's /full endpoint returns 406 unless the request allows a compressed response.
        self.session.headers["Accept-Encoding"] = "gzip, deflate"
        self.retries = retries
        self.timeout = timeout

    def _get(self, url, params=None, headers=None, retries=None):
        delay = 2
        retries = self.retries if retries is None else retries
        for attempt in range(retries + 1):
            try:
                resp = self.session.get(url, params=params, headers=headers, timeout=self.timeout, allow_redirects=False)
                while resp.is_redirect:
                    location = resp.headers.get("Location", "")
                    if "unblock.federalregister.gov" in location:
                        raise Blocked(url)
                    nxt = resp.next.url
                    # Request-specific headers (the GovInfo key) never follow a redirect off-host.
                    if urlparse(nxt).netloc != urlparse(url).netloc:
                        headers = None
                    resp = self.session.get(nxt, headers=headers, timeout=self.timeout, allow_redirects=False)
            except self._requests.RequestException:
                if attempt == retries:
                    raise
            else:
                if resp.status_code == 404:
                    raise NotFound(url)
                if resp.status_code < 500 and resp.status_code != 429:
                    resp.raise_for_status()
                    return resp
                if attempt == retries:
                    resp.raise_for_status()
            time.sleep(delay)
            delay *= 2

    def get_json(self, url, params=None):
        return self._get(url, params).json()

    def get_text(self, url, params=None):
        return self._get(url, params).text

    def get_document_html(self, doc: dict) -> tuple[str, str]:
        """Fetch a document's full-text HTML from GovInfo. Returns (html, route).

        Route "api": granule /htm with the key from GOVINFO_API_KEY in the
        X-Api-Key header (never in the URL, never logged); retries with
        exponential backoff on 429 and 5xx. Route "www": the public content
        link, tried when the key is absent or the API route fails. Raises
        TextUnavailable with both reasons if neither works."""
        urls = govinfo_urls(doc)
        key = os.environ.get(config.GOVINFO_KEY_ENV)
        reasons = []
        if key:
            try:
                return self._get(urls["api"], headers={"X-Api-Key": key}).text, "api"
            except NotFound:
                reasons.append("api: not_found (404)")
            except Blocked:
                reasons.append("api: redirected to a bot wall")
            except self._requests.HTTPError as e:
                reasons.append(f"api: HTTP {e.response.status_code if e.response is not None else '?'}")
            except self._requests.RequestException as e:
                reasons.append(f"api: request_error {type(e).__name__}")
        else:
            reasons.append(f"api: {config.GOVINFO_KEY_ENV} not set")
        try:
            return self._get(urls["www"]).text, "www"
        except NotFound:
            reasons.append("www: not_found (404)")
        except Blocked:
            reasons.append("www: redirected to a bot wall")
        except self._requests.HTTPError as e:
            reasons.append(f"www: HTTP {e.response.status_code if e.response is not None else '?'}")
        except self._requests.RequestException as e:
            reasons.append(f"www: request_error {type(e).__name__}")
        raise TextUnavailable("; ".join(reasons))


class FixtureClient:
    """Emulates the subset of both APIs the pipeline uses, backed by fixtures/."""

    offline = True

    def __init__(self, root: Path = FIXTURES_DIR):
        self.root = Path(root)
        self.documents = json.loads((self.root / "federal_register" / "documents.json").read_text())["results"]

    # -- Federal Register -------------------------------------------------
    def _search(self, params):
        agencies = set(params.get("conditions[agencies][]", []))
        types = {config.DOC_TYPES[t] for t in params.get("conditions[type][]", [])}
        gte = params.get("conditions[publication_date][gte]", "0000-00-00")
        lte = params.get("conditions[publication_date][lte]", "9999-99-99")
        # FR term search runs over full text; fixtures approximate it with title + abstract.
        term = params.get("conditions[term]", "").strip('"').lower()
        hits = [
            d for d in self.documents
            if (not agencies or agencies & {a.get("slug") for a in d.get("agencies", [])})
            and (not types or d.get("type") in types)
            and gte <= d.get("publication_date", "") <= lte
            and (not term or term in f"{d.get('title', '')} {d.get('abstract', '')}".lower())
        ]
        hits.sort(key=lambda d: (d["publication_date"], d["document_number"]))
        per_page = int(params.get("per_page", 20))
        page = int(params.get("page", 1))
        chunk = hits[(page - 1) * per_page: page * per_page]
        fields = params.get("fields[]")
        if fields:
            chunk = [{k: v for k, v in d.items() if k in fields} for d in chunk]
        total_pages = max(1, math.ceil(len(hits) / per_page))
        return {
            "count": len(hits),
            "total_pages": total_pages,
            "results": chunk,
            "next_page_url": "fixture://next" if page < total_pages else None,
        }

    # -- eCFR --------------------------------------------------------------
    def _ecfr(self, url, params):
        path = url[len(config.ECFR_API):].strip("/")
        parts = path.split("/")
        if parts[0] == "versions":  # versions/title-12.json?part=1006
            title = parts[1].split(".")[0]
            f = self.root / "ecfr" / f"versions-{title}-part-{params['part']}.json"
        elif parts[0] == "full":  # full/{date}/title-12.xml?part=..&section=..
            date, title = parts[1], parts[2].split(".")[0]
            kind = "section" if "section" in params else "appendix"
            f = self.root / "ecfr" / f"full-{date}-{title}-{kind}-{params[kind]}.xml"
        else:
            raise NotFound(url)
        if not f.exists():
            raise NotFound(url)
        return f.read_text()

    def get_json(self, url, params=None):
        params = params or {}
        if url == config.FR_API:
            return self._search(params)
        if url.startswith(config.ECFR_API):
            return json.loads(self._ecfr(url, params))
        raise NotFound(url)

    def get_document_html(self, doc: dict) -> tuple[str, str]:
        """Fixture stand-in for GovInfo: fixtures/text/<document_number>.txt."""
        f = self.root / "text" / f"{doc['document_number']}.txt"
        if not f.exists():
            raise NotFound(govinfo_urls(doc)["api"])
        return f.read_text(), "fixture"

    def get_text(self, url, params=None):
        params = params or {}
        if url.startswith(config.ECFR_API):
            return self._ecfr(url, params)
        name = url.rstrip("/").split("/")[-1]
        f = self.root / "text" / name
        if not f.exists():
            raise NotFound(url)
        return f.read_text()


def make_client(offline: bool):
    return FixtureClient() if offline else LiveClient()
