from __future__ import annotations
import socket
import ssl
import zlib
import gzip
from dataclasses import dataclass
from typing import Dict, Optional

from browser.url import URL


@dataclass
class Response:
    status: int
    headers: Dict[str, str]
    body: bytes
    encoding: str = "utf-8"


USER_AGENT = "MyBrowser/1.0 (ToyBrowser; +https://browser.engineering)"


def fetch(url: URL, max_redirects: int = 8) -> Response:
    cur = url
    redirects_left = max_redirects

    while True:
        status, headers, body = _request(cur)

        # redirects
        if status in (301, 302, 303, 307, 308) and "location" in headers and redirects_left > 0:
            cur = cur.resolve(headers["location"])
            redirects_left -= 1
            continue

        encoding = _guess_encoding(headers)
        return Response(status=status, headers=headers, body=body, encoding=encoding)


def _request(url: URL) -> tuple[int, Dict[str, str], bytes]:
    req = (
        f"GET {url.path} HTTP/1.1\r\n"
        f"Host: {url.host}\r\n"
        f"Connection: close\r\n"
        f"User-Agent: {USER_AGENT}\r\n"
        f"Accept: text/html, text/css, image/*;q=0.9, */*;q=0.8\r\n"
        f"Accept-Encoding: gzip, deflate\r\n"
        f"\r\n"
    ).encode("ascii", errors="ignore")

    s = socket.create_connection((url.host, url.port), timeout=12)
    if url.scheme == "https":
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=url.host)

    with s:
        s.sendall(req)
        raw = _read_all(s)

    # split headers/body
    sep = raw.find(b"\r\n\r\n")
    if sep == -1:
        return 0, {}, raw

    head = raw[:sep]
    body = raw[sep + 4 :]

    lines = head.split(b"\r\n")
    status_line = lines[0].decode("iso-8859-1", errors="replace")
    parts = status_line.split(" ", 2)
    status = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

    headers: Dict[str, str] = {}
    for line in lines[1:]:
        if b":" in line:
            k, v = line.split(b":", 1)
            headers[k.decode("iso-8859-1").strip().lower()] = v.decode("iso-8859-1").strip()

    # handle Transfer-Encoding: chunked
    if headers.get("transfer-encoding", "").lower() == "chunked":
        body = _decode_chunked(body)

    # handle Content-Encoding
    ce = headers.get("content-encoding", "").lower()
    if "gzip" in ce:
        try:
            body = gzip.decompress(body)
        except Exception:
            pass
    elif "deflate" in ce:
        try:
            body = zlib.decompress(body)
        except Exception:
            try:
                body = zlib.decompress(body, -zlib.MAX_WBITS)
            except Exception:
                pass

    return status, headers, body


def _read_all(sock: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        data = sock.recv(4096)
        if not data:
            break
        chunks.append(data)
    return b"".join(chunks)


def _decode_chunked(body: bytes) -> bytes:
    out = bytearray()
    i = 0
    n = len(body)

    while i < n:
        j = body.find(b"\r\n", i)
        if j == -1:
            break
        line = body[i:j].decode("ascii", errors="replace").strip()
        i = j + 2

        # chunk size may have extensions: "1a;foo=bar"
        if ";" in line:
            line = line.split(";", 1)[0].strip()

        try:
            size = int(line, 16)
        except ValueError:
            break

        if size == 0:
            break

        if i + size > n:
            break
        out.extend(body[i : i + size])
        i += size

        # trailing CRLF
        if i + 2 <= n and body[i : i + 2] == b"\r\n":
            i += 2

    return bytes(out)


def _guess_encoding(headers: Dict[str, str]) -> str:
    ct = headers.get("content-type", "")
    lower = ct.lower()
    if "charset=" in lower:
        charset = lower.split("charset=", 1)[1].split(";", 1)[0].strip()
        return charset or "utf-8"
    return "utf-8"
