"""HTTP clients. LiveClient talks to the Federal Register and eCFR APIs;
FixtureClient answers the same calls from fixtures/ with no network access."""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

from . import config
from .common import FIXTURES_DIR


class NotFound(Exception):
    pass


class Blocked(Exception):
    """The Federal Register redirected to its bot wall (unblock.federalregister.gov)."""


class TextUnavailable(Exception):
    """Full text could not be fetched; the message is the logged reason."""


TEXT_RETRY_USER_AGENT = "servicing-reg-watch/1.0 (research project)"


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
                    resp = self.session.get(resp.next.url, headers=headers, timeout=self.timeout, allow_redirects=False)
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

    def get_full_text(self, url):
        """Fetch a document's full text. On the FR bot wall, retry once with a
        descriptive User-Agent; no further retries. Raises Blocked or
        TextUnavailable with the reason."""
        try:
            return self._get(url, retries=0).text
        except Blocked:
            pass
        except self._requests.RequestException as e:
            raise TextUnavailable(f"request_error: {type(e).__name__}") from e
        try:
            return self._get(url, headers={"User-Agent": TEXT_RETRY_USER_AGENT}, retries=0).text
        except Blocked:
            raise Blocked("fr_bot_wall: redirected to unblock.federalregister.gov (after User-Agent retry)")
        except self._requests.RequestException as e:
            raise TextUnavailable(f"request_error on User-Agent retry: {type(e).__name__}") from e


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

    def get_full_text(self, url):
        return self.get_text(url)

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
