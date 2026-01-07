from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import base64

import tkinter as tk

from browser.url import URL
from browser.http import fetch
from browser.html import HTMLParser
from browser.css import CSSParser
from browser.style import StyleEngine
from browser.layout import LayoutEngine
from browser.paint import Painter, DisplayItem, DisplayText, DisplayImage
from browser.dom import ElementNode, TextNode, Node

Hitbox = Tuple[int, int, int, int, str]


@dataclass
class Tab:
    viewport: object
    scroll_y: int = 0
    url: Optional[URL] = None
    title: str = "New Tab"

    html_source: str = ""
    display_list: List[DisplayItem] = None
    hitboxes: List[Hitbox] = None

    history: List[str] = None
    history_index: int = -1

    doc_height: int = 0
    image_cache: Dict[str, object] = None

    def __post_init__(self) -> None:
        self.display_list = []
        self.hitboxes = []
        self.history = []
        self.image_cache = {}

    def current_url_str(self) -> str:
        return "" if self.url is None else self.url.to_string()

    def can_go_back(self) -> bool:
        return self.history_index > 0

    def can_go_forward(self) -> bool:
        return 0 <= self.history_index < len(self.history) - 1

    def load(self, url_str: str, push_history: bool = True) -> None:
        self.url = URL.parse(url_str)
        resp = fetch(self.url)
        self.html_source = resp.body.decode(resp.encoding, errors="replace")

        dom = HTMLParser(self.html_source).parse()

        css_text = self._collect_all_css(dom)
        rules = CSSParser(css_text).parse()

        styled = StyleEngine(rules).style(dom)
        layout_tree = LayoutEngine(self.viewport).layout(styled)
        self.doc_height = int(getattr(layout_tree, "height", 0) or 0)

        self.display_list = Painter(image_loader=self._load_image).paint(layout_tree)
        self.scroll_y = 0
        self.hitboxes = []

        self.title = self._extract_title(dom) or self.url.host

        if push_history:
            if self.history_index < len(self.history) - 1:
                self.history = self.history[: self.history_index + 1]
            self.history.append(self.url.to_string())
            self.history_index = len(self.history) - 1

    def reload(self) -> None:
        if self.url:
            self.load(self.url.to_string(), push_history=False)

    def go_back(self) -> None:
        if self.can_go_back():
            self.history_index -= 1
            self.load(self.history[self.history_index], push_history=False)

    def go_forward(self) -> None:
        if self.can_go_forward():
            self.history_index += 1
            self.load(self.history[self.history_index], push_history=False)

    def _max_scroll(self) -> int:
        vh = int(getattr(self.viewport, "height", 0) or 0)
        return max(0, int(self.doc_height) - vh)

    def scroll_by(self, dy: int) -> None:
        self.scroll_y = max(0, min(self.scroll_y + dy, self._max_scroll()))

    def click(self, x: int, y: int) -> None:
        for x1, y1, x2, y2, href in reversed(self.hitboxes):
            if x1 <= x <= x2 and y1 <= y <= y2:
                if not self.url:
                    return
                self.load(self.url.resolve(href).to_string(), push_history=True)
                return

    def render(self, canvas) -> None:
        # clamp
        self.scroll_y = max(0, min(self.scroll_y, self._max_scroll()))

        self.hitboxes = []
        for item in self.display_list:
            bbox = item.draw(canvas, scroll_y=self.scroll_y) if hasattr(item, "draw") else None
            if bbox:
                href = None
                if isinstance(item, DisplayText) and item.href:
                    href = item.href
                if isinstance(item, DisplayImage) and item.href:
                    href = item.href
                if href:
                    x1, y1, x2, y2 = bbox
                    self.hitboxes.append((x1, y1, x2, y2, href))

        self._draw_scrollbar(canvas)

    def _draw_scrollbar(self, canvas) -> None:
        vh = int(getattr(self.viewport, "height", 0) or 0)
        vw = int(getattr(self.viewport, "width", 0) or 0)
        max_scroll = self._max_scroll()
        if max_scroll <= 0 or vh <= 0:
            return
        track_w = 10
        margin = 4
        x1 = vw - track_w - margin
        x2 = vw - margin

        thumb_h = max(24, int(vh * (vh / max(self.doc_height, 1))))
        thumb_y = int((vh - thumb_h) * (self.scroll_y / max_scroll))

        canvas.create_rectangle(x1, 0, x2, vh, outline="", fill="#efefef")
        canvas.create_rectangle(x1, thumb_y, x2, thumb_y + thumb_h, outline="", fill="#bdbdbd")

    # ---- CSS: inline <style> + external <link rel="stylesheet"> ----

    def _collect_all_css(self, root: ElementNode) -> str:
        chunks: List[str] = []
        chunks.append(self._extract_style_text(root))
        for href in self._extract_stylesheet_links(root):
            if not self.url:
                continue
            css_url = self.url.resolve(href)
            try:
                r = fetch(css_url)
                chunks.append(r.body.decode(r.encoding, errors="replace"))
            except Exception:
                continue
        return "\n\n".join([c for c in chunks if c.strip()])

    def _extract_style_text(self, root: ElementNode) -> str:
        chunks: List[str] = []
        def walk(n: Node) -> None:
            if isinstance(n, ElementNode) and n.tag == "style":
                chunks.append(self._text_content(n))
                return
            if isinstance(n, ElementNode):
                for c in n.children:
                    walk(c)
        walk(root)
        return "\n".join(chunks)

    def _extract_stylesheet_links(self, root: ElementNode) -> List[str]:
        hrefs: List[str] = []
        def walk(n: Node) -> None:
            if isinstance(n, ElementNode) and n.tag == "link":
                rel = (n.attributes.get("rel") or "").lower()
                href = (n.attributes.get("href") or "").strip()
                if "stylesheet" in rel and href:
                    hrefs.append(href)
            if isinstance(n, ElementNode):
                for c in n.children:
                    walk(c)
        walk(root)
        return hrefs

    def _text_content(self, el: ElementNode) -> str:
        out: List[str] = []
        def walk(n: Node) -> None:
            if isinstance(n, TextNode):
                out.append(n.text)
            elif isinstance(n, ElementNode):
                for c in n.children:
                    walk(c)
        walk(el)
        return "".join(out)

    # ---- Title ----
    def _extract_title(self, root: ElementNode) -> str:
        # very small title extraction
        def find_title(n: Node) -> Optional[str]:
            if isinstance(n, ElementNode) and n.tag == "title":
                return self._text_content(n).strip()
            if isinstance(n, ElementNode):
                for c in n.children:
                    t = find_title(c)
                    if t:
                        return t
            return None
        return find_title(root) or ""

    # ---- Images ----
    def _load_image(self, src: str) -> object:
        if not src or not self.url:
            return None
        abs_url = self.url.resolve(src).to_string()
        if abs_url in self.image_cache:
            return self.image_cache[abs_url]

        try:
            r = fetch(URL.parse(abs_url))
            data = r.body
            is_png = data.startswith(b"\x89PNG\r\n\x1a\n")
            is_gif = data.startswith(b"GIF87a") or data.startswith(b"GIF89a")

            if is_png or is_gif:
                b64 = base64.b64encode(data).decode("ascii")
                img = tk.PhotoImage(data=b64)
                self.image_cache[abs_url] = img
                return img

            # JPG support if Pillow is installed (optional)
            try:
                from PIL import Image, ImageTk  # type: ignore
                import io
                im = Image.open(io.BytesIO(data))
                img = ImageTk.PhotoImage(im)
                self.image_cache[abs_url] = img
                return img
            except Exception:
                self.image_cache[abs_url] = None
                return None

        except Exception:
            self.image_cache[abs_url] = None
            return None
