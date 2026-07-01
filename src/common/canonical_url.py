"""URL canonicalization for stable article identification."""

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "ref",
        "mc_cid",
        "mc_eid",
    }
)


def canonicalize_url(url: str) -> str:
    """Normalize URL so the same article always maps to one identifier."""
    parsed = urlparse(url.strip())
    query_params = parse_qs(parsed.query, keep_blank_values=False)
    clean_params = {
        key: value
        for key, value in query_params.items()
        if key.lower() not in TRACKING_PARAMS
    }
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (
            "https",
            parsed.netloc.lower(),
            path,
            "",
            urlencode(clean_params, doseq=True),
            "",
        )
    )
