from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple, Union

from browser.layout import LayoutBox
from browser.dom import TextNode, ElementNode

BBox = Tuple[int, int, int, int]


@dataclass
class DisplayRect:
    x: int
    y: int
    w: int
    h: int
    fill: str
    def draw(self, canvas, scroll_y: int) -> None:
        dy = self.y - scroll_y
        canvas.create_rectangle(self.x, dy, self.x + self.w, dy + self.h, outline="", fill=self.fill)


@dataclass
class DisplayText:
    x: int
    y: int
    text: str
    font_size: int
    color: str
    href: Optional[str] = None
    def draw(self, canvas, scroll_y: int) -> Optional[BBox]:
        dy = self.y - scroll_y
        if self.href:
            item = canvas.create_text(self.x, dy, anchor="nw", text=self.text,
                                      fill="blue", font=("Arial", self.font_size, "underline"))
        else:
            item = canvas.create_text(self.x, dy, anchor="nw", text=self.text,
                                      fill=self.color, font=("Arial", self.font_size))
        return canvas.bbox(item) or None


@dataclass
class DisplayImage:
    x: int
    y: int
    w: int
    h: int
    src: str
    href: Optional[str] = None
    image_obj: object = None
    def draw(self, canvas, scroll_y: int) -> Optional[BBox]:
        dy = self.y - scroll_y
        if self.image_obj is not None:
            canvas.create_image(self.x, dy, anchor="nw", image=self.image_obj)
        else:
            canvas.create_rectangle(self.x, dy, self.x + self.w, dy + self.h, outline="gray")
            canvas.create_text(self.x + 4, dy + 4, anchor="nw", text="[image]", fill="gray", font=("Arial", 10))
        return (self.x, dy, self.x + self.w, dy + self.h)


DisplayItem = Union[DisplayRect, DisplayText, DisplayImage]


class Painter:
    def __init__(self, image_loader: Optional[Callable[[str], object]] = None) -> None:
        self.image_loader = image_loader

    def paint(self, root: LayoutBox) -> List[DisplayItem]:
        out: List[DisplayItem] = []
        self._walk(root, out)
        return out

    def _walk(self, box: LayoutBox, out: List[DisplayItem]) -> None:
        node = box.styled.node

        # background
        if isinstance(node, ElementNode):
            bg = box.styled.style.get("background-color") or box.styled.style.get("background")
            if bg and bg.lower() not in ("transparent", "none"):
                out.append(DisplayRect(box.x, box.y, box.width, box.height, bg))

            if node.tag == "img":
                src = (node.attributes.get("src") or "").strip()
                href = self._find_link_href_for_element(node)
                img_obj = self.image_loader(src) if (self.image_loader and src) else None
                out.append(DisplayImage(box.x, box.y, box.width, box.height, src, href=href, image_obj=img_obj))

        # text
        if isinstance(node, TextNode) and node.text:
            href = self._find_link_href_for_text(node)
            fs = 16
            raw = box.styled.style.get("font-size")
            if raw:
                try:
                    fs = int(float(str(raw).replace("px", "").strip()))
                except Exception:
                    fs = 16
            color = box.styled.style.get("color", "black")
            out.append(DisplayText(box.x, box.y, node.text, fs, color, href=href))

        for c in box.children:
            self._walk(c, out)

    def _find_link_href_for_text(self, t: TextNode) -> Optional[str]:
        p = t.parent
        while p is not None:
            if isinstance(p, ElementNode) and p.tag == "a":
                return p.attributes.get("href")
            p = p.parent
        return None

    def _find_link_href_for_element(self, el: ElementNode) -> Optional[str]:
        p = el.parent
        while p is not None:
            if isinstance(p, ElementNode) and p.tag == "a":
                return p.attributes.get("href")
            p = p.parent
        return None
