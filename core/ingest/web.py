"""Website onboarding: fetch a company's site and turn it into setup material.

Two extractions with different trust levels:

- **Channels — deterministic.** Social links on the page (LinkedIn, X, GitHub,
  Discord, a blog, a newsletter) are facts, not inference; they prefill the
  channel registry with real handles.
- **Brand voice/ICP — drafted.** The visible page text feeds the ImportProvider
  brand extractor (mock today, an LLM extractor behind the same interface),
  and the result stays a DRAFT the lead confirms.

The fetch is lead-triggered but still SSRF-guarded: http(s) only, and the host
must not resolve to a private/loopback address.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

_TIMEOUT_SECONDS = 10.0
_MAX_TEXT_CHARS = 20_000

# href fragment → the platform name the rest of the app uses (platform_specs).
_CHANNEL_PATTERNS: list[tuple[str, str]] = [
    ("linkedin.com/", "LinkedIn"),
    ("twitter.com/", "X / Twitter"),
    ("x.com/", "X / Twitter"),
    ("github.com/", "GitHub / CLI"),
    ("discord.gg/", "Community"),
    ("discord.com/invite", "Community"),
    ("slack.com/", "Community"),
    ("t.me/", "Community"),
    ("youtube.com/", "YouTube"),
    ("substack.com", "Email"),
    ("mailto:", "Email"),
]


@dataclass(frozen=True)
class DetectedChannel:
    platform: str
    handle: str


class _PageParser(HTMLParser):
    """Visible text + links, stdlib-only (no bs4 dependency)."""

    _SKIP = {"script", "style", "noscript", "svg", "template"}

    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []
        self.hrefs: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        if tag == "a":
            href = next((v for k, v in attrs if k == "href" and v), None)
            if href:
                self.hrefs.append(href)
        if tag == "meta":
            attr_map = {k: (v or "") for k, v in attrs}
            if attr_map.get("name") in {"description", "og:description"} or attr_map.get(
                "property"
            ) in {"og:description", "og:title"}:
                content = attr_map.get("content", "").strip()
                if content:
                    self.chunks.append(content)

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            cleaned = data.strip()
            if cleaned:
                self.chunks.append(cleaned)


def assert_public_http_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("The URL must be an http(s) address with a hostname.")
    try:
        resolved = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise ValueError("The host could not be resolved.") from exc
    for family_info in resolved:
        address = ipaddress.ip_address(family_info[4][0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
        ):
            raise ValueError("The host resolves to a private address — refusing to fetch.")
    return raw_url


def _client_factory() -> httpx.Client:
    """Factory for the fetch client (patched in tests)."""

    return httpx.Client(timeout=_TIMEOUT_SECONDS, follow_redirects=True)


def _detect_channels(base_url: str, hrefs: list[str]) -> list[DetectedChannel]:
    found: dict[str, DetectedChannel] = {}
    for href in hrefs:
        absolute = urljoin(base_url, href)
        lowered = absolute.lower()
        for fragment, platform in _CHANNEL_PATTERNS:
            if fragment in lowered and platform not in found:
                handle = absolute[7:] if lowered.startswith("mailto:") else absolute
                found[platform] = DetectedChannel(platform=platform, handle=handle)
                break
        # A /blog path on the same site is the Blog channel.
        if "Blog" not in found:
            parsed = urlparse(absolute)
            if parsed.netloc == urlparse(base_url).netloc and (
                parsed.path.rstrip("/").endswith("/blog") or parsed.netloc.startswith("blog.")
            ):
                found["Blog"] = DetectedChannel(platform="Blog", handle=absolute)
    return list(found.values())


def fetch_site(url: str) -> tuple[str, list[DetectedChannel]]:
    """(visible text, detected channels) for a public site. Raises ValueError on
    a bad/private URL and httpx.HTTPError on network failure."""
    safe_url = assert_public_http_url(url)
    with _client_factory() as client:
        response = client.get(safe_url)
        response.raise_for_status()
        html = response.text
    parser = _PageParser()
    parser.feed(html)
    text = " ".join(parser.chunks)[:_MAX_TEXT_CHARS]
    return text, _detect_channels(safe_url, parser.hrefs)
