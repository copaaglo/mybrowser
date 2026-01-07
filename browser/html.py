from __future__ import annotations
import re
from typing import List

from browser.dom import ElementNode, TextNode

TAG_RE = re.compile(r"<(/?)([a-zA-Z0-9]+)([^>]*)>")
RAW_TEXT_TAGS = {"script", "style"}  # do not parse inner tags


class HTMLParser:
    def __init__(self, source: str) -> None:
        self.source = source or ""

    def parse(self) -> ElementNode:
        root = ElementNode(tag="html")
        stack: List[ElementNode] = [root]

        i = 0
        while True:
            m = TAG_RE.search(self.source, i)
            if not m:
                self._emit_text(stack[-1], self.source[i:], raw=(stack[-1].tag in RAW_TEXT_TAGS))
                break

            start, end = m.span()

            # text before
            if start > i:
                self._emit_text(stack[-1], self.source[i:start], raw=(stack[-1].tag in RAW_TEXT_TAGS))

            closing, tag, attr_text = m.group(1), m.group(2).lower(), m.group(3)
            i = end

            if closing:
                while len(stack) > 1 and stack[-1].tag != tag:
                    stack.pop()
                if len(stack) > 1:
                    stack.pop()
                continue

            el = ElementNode(tag=tag, attributes=self._parse_attrs(attr_text))
            stack[-1].append(el)

            # void tags
            if tag in ("br", "img", "meta", "link", "input", "hr"):
                continue

            stack.append(el)

            # RAW TEXT: consume directly until closing tag
            if tag in RAW_TEXT_TAGS:
                close_pat = f"</{tag}>"
                close_idx = self.source.lower().find(close_pat, i)
                if close_idx == -1:
                    raw = self.source[i:]
                    if raw:
                        el.append(TextNode(text=raw))
                    i = len(self.source)
                else:
                    raw = self.source[i:close_idx]
                    if raw:
                        el.append(TextNode(text=raw))
                    i = close_idx + len(close_pat)
                    stack.pop()

        return root

    def _emit_text(self, parent: ElementNode, text: str, raw: bool) -> None:
        if not text:
            return
        if raw:
            parent.append(TextNode(text=text))
            return
        # collapse whitespace
        t = re.sub(r"\s+", " ", text).strip()
        if t:
            parent.append(TextNode(text=t))

    def _parse_attrs(self, s: str) -> dict[str, str]:
        attrs: dict[str, str] = {}
        # supports key="value" / key='value' / key=value
        for k, v in re.findall(
            r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(".*?"|\'.*?\'|[^\s"]+)',
            s,
        ):
            v = v.strip()
            if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
                v = v[1:-1]
            attrs[k.lower()] = v
        return attrs
