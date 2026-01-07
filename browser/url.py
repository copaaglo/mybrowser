from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse


def _default_port(scheme: str) -> int:
    return 443 if scheme == "https" else 80


def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    # keep query out; normalize only path part
    parts = path.split("?", 1)
    p = parts[0]
    if not p.startswith("/"):
        p = "/" + p
    # basic dot-segment removal
    segs = []
    for seg in p.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if segs:
                segs.pop()
        else:
            segs.append(seg)
    norm = "/" + "/".join(segs)
    if len(parts) == 2:
        norm += "?" + parts[1]
    return norm


@dataclass(frozen=True)
class URL:
    scheme: str
    host: str
    port: int
    path: str  # includes optional query

    @staticmethod
    def parse(raw: str) -> "URL":
        raw = raw.strip()
        if "://" not in raw:
            raw = "http://" + raw

        p = urlparse(raw)
        scheme = (p.scheme or "http").lower()
        
        if scheme == "file":
            # For file URLs, we don't expect a host
            host = ""
            path = p.path
            port = 0
            return URL(scheme=scheme, host=host, port=port, path=path)

        host = p.hostname or ""
        if not host:
            raise ValueError(f"Invalid URL (missing host): {raw}")

        port = int(p.port) if p.port is not None else _default_port(scheme)

        path = p.path or "/"
        if p.query:
            path += "?" + p.query
        path = _normalize_path(path)

        return URL(scheme=scheme, host=host, port=port, path=path)

    def to_string(self) -> str:
        default = _default_port(self.scheme)
        netloc = self.host if self.port == default else f"{self.host}:{self.port}"
        # path already includes query if present
        if "?" in self.path:
            path, query = self.path.split("?", 1)
        else:
            path, query = self.path, ""
        return urlunparse((self.scheme, netloc, path, "", query, ""))

    def resolve(self, link: str) -> "URL":
        link = (link or "").strip()
        if not link:
            return self

        # absolute
        if "://" in link:
            return URL.parse(link)

        # strip fragment
        link = link.split("#", 1)[0]
        if not link:
            return self

        # scheme-relative //example.com
        if link.startswith("//"):
            return URL.parse(f"{self.scheme}:{link}")

        # absolute path
        if link.startswith("/"):
            return URL(self.scheme, self.host, self.port, _normalize_path(link))

        # relative path
        base_path = self.path.split("?", 1)[0]
        if not base_path.endswith("/"):
            base_dir = base_path.rsplit("/", 1)[0] + "/"
        else:
            base_dir = base_path

        joined = base_dir + link
        return URL(self.scheme, self.host, self.port, _normalize_path(joined))
