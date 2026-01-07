from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class SimpleSelector:
    tag: Optional[str] = None
    cls: Optional[str] = None
    id: Optional[str] = None

    def specificity(self) -> int:
        if self.id:
            return 100
        if self.cls:
            return 10
        if self.tag:
            return 1
        return 0


@dataclass(frozen=True)
class Selector:
    # supports descendant chain length 2: left right
    right: SimpleSelector
    left: Optional[SimpleSelector] = None

    def specificity(self) -> int:
        s = self.right.specificity()
        if self.left:
            s += self.left.specificity()
        return s


@dataclass(frozen=True)
class Rule:
    selector: Selector
    declarations: Dict[str, str]
    order: int  # source order


class CSSParser:
    def __init__(self, source: str) -> None:
        self.source = source or ""

    def parse(self) -> List[Rule]:
        s = self._strip_comments(self.source)
        rules: List[Rule] = []
        order = 0

        while True:
            s = s.strip()
            if not s or "{" not in s:
                break

            selector_text, rest = s.split("{", 1)
            selector_text = selector_text.strip()
            if "}" not in rest:
                break

            block, s = rest.split("}", 1)
            decls = self._parse_declarations(block)

            # selector lists: "h1,h2,p"
            selectors = [x.strip() for x in selector_text.split(",") if x.strip()]
            for sel in selectors:
                selector = self._parse_selector(sel)
                if selector is not None and decls:
                    rules.append(Rule(selector=selector, declarations=decls, order=order))
                    order += 1

        return rules

    def _parse_selector(self, sel: str) -> Optional[Selector]:
        parts = [p for p in sel.split() if p]
        if len(parts) == 1:
            right = self._parse_simple(parts[0])
            return Selector(right=right) if right else None
        if len(parts) == 2:
            left = self._parse_simple(parts[0])
            right = self._parse_simple(parts[1])
            if left and right:
                return Selector(left=left, right=right)
        return None

    def _parse_simple(self, token: str) -> Optional[SimpleSelector]:
        token = token.strip()
        if not token:
            return None
        if token.startswith("#") and len(token) > 1:
            return SimpleSelector(id=token[1:])
        if token.startswith(".") and len(token) > 1:
            return SimpleSelector(cls=token[1:])
        t = token.lower()
        return SimpleSelector(tag=t) if t.isidentifier() else None

    def _parse_declarations(self, block: str) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for part in block.split(";"):
            part = part.strip()
            if not part or ":" not in part:
                continue
            k, v = part.split(":", 1)
            out[k.strip().lower()] = v.strip()
        return out

    def _strip_comments(self, s: str) -> str:
        out = []
        i = 0
        while i < len(s):
            if i + 1 < len(s) and s[i] == "/" and s[i + 1] == "*":
                j = s.find("*/", i + 2)
                if j == -1:
                    break
                i = j + 2
            else:
                out.append(s[i])
                i += 1
        return "".join(out)


def parse_inline_style(style_attr: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    s = style_attr or ""
    for part in s.split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        k, v = part.split(":", 1)
        out[k.strip().lower()] = v.strip()
    return out
