"""URL canonicalization for deduplication and citation matching."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid", "ref", "mc_cid", "mc_eid"}

# Second-level public suffixes common enough to matter for publisher grouping.
_SLD = {"co.uk", "ac.uk", "gov.uk", "org.uk", "com.au", "co.jp", "com.br", "co.in", "gov.au"}


def canonicalize(url: str) -> str:
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if parts.port and parts.port not in (80, 443):
        host = f"{host}:{parts.port}"
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query) if k.lower() not in _TRACKING))
    path = parts.path.rstrip("/") or ""
    return urlunsplit(("https", host, path, query, ""))


def registrable_domain(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in _SLD:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:]) if len(labels) >= 2 else host
