from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import tkinter.font as tkfont

from browser.style import StyledNode
from browser.dom import TextNode, ElementNode

@dataclass
class LayoutBox:
    styled: StyledNode
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    children: List["LayoutBox"] = field(default_factory=list)

LayoutTree = LayoutBox

BLOCK_TAGS = {
    "html", "body", "div", "section", "article", "header", "footer", "nav", "main",
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
}
INLINE_TAGS = {"span", "a", "b", "i", "em", "strong", "small", "code", "br", "img"}

DEFAULT_MARGINS = {"p": (10, 10), "h1": (18, 12), "h2": (16, 10), "h3": (14, 8), "li": (2, 2), "ul": (6, 6), "ol": (6, 6)}
DEFAULT_FONT_SIZES = {"h1": 32, "h2": 26, "h3": 22, "p": 16, "li": 16}

PAGE_PADDING_X = 14
PAGE_PADDING_Y = 14
LIST_INDENT = 26
BULLET_GAP = 10


def _parse_len(v: Optional[str], default: int = 0) -> int:
    if not v:
        return default
    s = str(v).strip().lower()
    if s.endswith("px"):
        s = s[:-2].strip()
    try:
        return int(float(s))
    except Exception:
        return default


def _parse_box_shorthand(v: Optional[str]) -> Tuple[int, int, int, int]:
    if not v:
        return (0, 0, 0, 0)
    parts = [p for p in v.replace(",", " ").split() if p]
    nums = [_parse_len(p, 0) for p in parts]
    if len(nums) == 1:
        a = nums[0]; return (a, a, a, a)
    if len(nums) == 2:
        tb, lr = nums; return (tb, lr, tb, lr)
    if len(nums) == 3:
        t, lr, b = nums; return (t, lr, b, lr)
    if len(nums) >= 4:
        t, r, b, l = nums[:4]; return (t, r, b, l)
    return (0, 0, 0, 0)


class LayoutEngine:
    def __init__(self, viewport) -> None:
        self.viewport = viewport
        self._font_cache: Dict[Tuple[str, int], tkfont.Font] = {}

    def layout(self, styled_root: StyledNode) -> LayoutTree:
        root = LayoutBox(styled=styled_root, x=0, y=0, width=int(self.viewport.width), height=0)
        cursor_y = PAGE_PADDING_Y
        cursor_y = self._layout_block_children(root, styled_root.children, PAGE_PADDING_X, cursor_y,
                                              root.width - 2 * PAGE_PADDING_X, list_level=0)
        root.height = max(int(self.viewport.height), cursor_y + PAGE_PADDING_Y)
        return root

    def _layout_block_children(self, parent: LayoutBox, children: List[StyledNode],
                              x: int, y: int, width: int, list_level: int) -> int:
        cursor_y = y

        for child in children:
            tag = self._tag(child)
            display = self._display(child)

            if display == "block":
                # margins
                mt, mb = DEFAULT_MARGINS.get(tag, (0, 0))
                sh_m = _parse_box_shorthand(child.style.get("margin"))
                mt = _parse_len(child.style.get("margin-top"), sh_m[0] or mt)
                mb = _parse_len(child.style.get("margin-bottom"), sh_m[2] or mb)
                ml = _parse_len(child.style.get("margin-left"), sh_m[3])
                mr = _parse_len(child.style.get("margin-right"), sh_m[1])

                # padding
                sh_p = _parse_box_shorthand(child.style.get("padding"))
                pt = _parse_len(child.style.get("padding-top"), sh_p[0])
                pr = _parse_len(child.style.get("padding-right"), sh_p[1])
                pb = _parse_len(child.style.get("padding-bottom"), sh_p[2])
                pl = _parse_len(child.style.get("padding-left"), sh_p[3])

                cursor_y += mt

                # list indentation
                level = list_level + 1 if tag in ("ul", "ol") else list_level
                indent_x = x + (LIST_INDENT * list_level) + ml
                indent_w = max(80, width - (LIST_INDENT * list_level) - ml - mr)

                box = LayoutBox(styled=child, x=indent_x, y=cursor_y, width=indent_w, height=0)
                parent.children.append(box)

                content_x = indent_x + pl
                content_y = cursor_y + pt
                content_w = max(50, indent_w - pl - pr)

                if tag == "li":
                    fs = self._font_size("li", child)
                    bullet_w = self._measure("•", fs)

                    bullet = TextNode(text="•")
                    bullet.parent = child.node
                    bullet_styled = StyledNode(node=bullet, style=dict(child.style) | {"font-size": str(fs)}, children=[])

                    box.children.append(LayoutBox(styled=bullet_styled, x=content_x, y=content_y,
                                                  width=bullet_w, height=int(fs * 1.35)))

                    li_x = content_x + bullet_w + BULLET_GAP
                    li_w = max(50, content_w - (bullet_w + BULLET_GAP))

                    if self._contains_inline(child):
                        inner_h = self._layout_inline(box, child, li_x, content_y, li_w, "li")
                    else:
                        start = content_y
                        end = self._layout_block_children(box, child.children, li_x, content_y, li_w, level)
                        inner_h = max(0, end - start)

                else:
                    if self._contains_inline(child):
                        inner_h = self._layout_inline(box, child, content_x, content_y, content_w, tag)
                    else:
                        start = content_y
                        end = self._layout_block_children(box, child.children, content_x, content_y, content_w, level)
                        inner_h = max(0, end - start)

                box.height = pt + inner_h + pb
                cursor_y += box.height + mb

            else:
                pseudo = LayoutBox(styled=child, x=x, y=cursor_y, width=width, height=0)
                parent.children.append(pseudo)
                pseudo.height = self._layout_inline(pseudo, child, x, cursor_y, width, self._tag(child))
                cursor_y += pseudo.height

        return cursor_y

    def _layout_inline(self, parent: LayoutBox, styled: StyledNode, x: int, y: int, width: int, ctx_tag: str) -> int:
        tokens = self._tokens(styled)

        fs = self._font_size(ctx_tag, styled)
        line_h = int(fs * 1.35)
        max_x = x + width
        cx, cy = x, y

        def newline():
            nonlocal cx, cy
            cx = x
            cy += line_h

        for t in tokens:
            kind = t[0]
            if kind == "br":
                newline()
                continue

            if kind in ("word", "space"):
                text, origin_text = t[1], t[2]
                if kind == "space" and cx == x:
                    continue
                w = self._measure(text, fs)
                if cx + w > max_x and kind != "space":
                    newline()

                synthetic = TextNode(text=text)
                synthetic.parent = origin_text.parent if origin_text else None
                st = dict(styled.style)
                st["font-size"] = str(fs)
                parent.children.append(LayoutBox(styled=StyledNode(node=synthetic, style=st, children=[]),
                                                x=cx, y=cy, width=w, height=line_h))
                cx += w
                continue

            if kind == "img":
                src, w_attr, h_attr, origin_el = t[1], t[2], t[3], t[4]
                iw = _parse_len(w_attr, 180)
                ih = _parse_len(h_attr, 180)
                if cx + iw > max_x and cx != x:
                    newline()
                st = dict(styled.style)
                st["display"] = "inline"
                parent.children.append(LayoutBox(styled=StyledNode(node=origin_el, style=st, children=[]),
                                                x=cx, y=cy, width=iw, height=max(ih, line_h)))
                cx += iw
                continue

        return max(line_h, (cy - y) + line_h)

    def _tokens(self, styled: StyledNode):
        out = []

        def walk(n: StyledNode):
            node = n.node
            if isinstance(node, TextNode):
                txt = node.text or ""
                cur = ""
                for ch in txt:
                    if ch.isspace():
                        if cur:
                            out.append(("word", cur, node))
                            cur = ""
                        out.append(("space", " ", node))
                    else:
                        cur += ch
                if cur:
                    out.append(("word", cur, node))
                return

            if isinstance(node, ElementNode):
                if node.tag == "br":
                    out.append(("br", "", None))
                    return
                if node.tag == "img":
                    out.append(("img", node.attributes.get("src", ""), node.attributes.get("width"), node.attributes.get("height"), node))
                    return
                for c in n.children:
                    walk(c)

        walk(styled)
        return out

    def _tag(self, styled: StyledNode) -> str:
        return styled.node.tag if isinstance(styled.node, ElementNode) else ""

    def _display(self, styled: StyledNode) -> str:
        n = styled.node
        if isinstance(n, TextNode):
            return "inline"
        if isinstance(n, ElementNode):
            if n.tag in BLOCK_TAGS:
                return "block"
            if n.tag in INLINE_TAGS:
                return "inline"
        return "block"

    def _contains_inline(self, styled: StyledNode) -> bool:
        stack = [styled]
        while stack:
            s = stack.pop()
            if isinstance(s.node, TextNode):
                return True
            if isinstance(s.node, ElementNode) and self._display(s) == "inline":
                return True
            stack.extend(s.children)
        return False

    def _font_size(self, tag: str, styled: StyledNode) -> int:
        raw = styled.style.get("font-size")
        if raw:
            try:
                return int(float(str(raw).replace("px", "").strip()))
            except Exception:
                pass
        return DEFAULT_FONT_SIZES.get(tag, 16)

    def _font(self, size: int) -> tkfont.Font:
        key = ("Arial", int(size))
        f = self._font_cache.get(key)
        if f is None:
            f = tkfont.Font(family="Arial", size=int(size))
            self._font_cache[key] = f
        return f

    def _measure(self, text: str, size: int) -> int:
        return int(self._font(size).measure(text)) if text else 0
