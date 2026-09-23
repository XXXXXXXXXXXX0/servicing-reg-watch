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


class LiveClient:
    offline = False

    def __init__(self, retries: int = 4, timeout: int = 60):
        import requests  # imported lazily so offline runs never need it

        self._requests = requests
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "servicing-reg-watch/1 (regulatory change monitoring)"
        self.retries = retries
        self.timeout = timeout

    def _get(self, url, params=None):
        delay = 2
        for attempt in range(self.retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except self._requests.RequestException:
                if attempt == self.retries:
                    raise
            else:
                if resp.status_code == 404:
                    raise NotFound(url)
                if resp.status_code < 500 and resp.status_code != 429:
                    resp.raise_for_status()
                    return resp
                if attempt == self.retries:
                    resp.raise_for_status()
            time.sleep(delay)
            delay *= 2

    def get_json(self, url, params=None):
        return self._get(url, params).json()

    def get_text(self, url, params=None):
        return self._get(url, params).text


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
        hits = [
            d for d in self.documents
            if (not agencies or agencies & {a.get("slug") for a in d.get("agencies", [])})
            and (not types or d.get("type") in types)
            and gte <= d.get("publication_date", "") <= lte
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
            f = self.root / "ecfr" / f"full-{date}-{title}-section-{params['section']}.xml"
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
