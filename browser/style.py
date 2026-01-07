from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from browser.dom import ElementNode, TextNode, Node
from browser.css import Rule, Selector, SimpleSelector, parse_inline_style

UA_DEFAULTS = {
    "font-size": "16",
    "color": "black",
    "background-color": "transparent",
    "margin": "0",
    "padding": "0",
}

INHERITED = {"font-size", "color"}


@dataclass
class StyledNode:
    node: Node
    style: Dict[str, str] = field(default_factory=dict)
    children: List["StyledNode"] = field(default_factory=list)


class StyleEngine:
    def __init__(self, rules: List[Rule]) -> None:
        self.rules = rules or []

    def style(self, dom: ElementNode) -> StyledNode:
        return self._style_node(dom, parent_style=None)

    def _style_node(self, node: Node, parent_style: Optional[Dict[str, str]]) -> StyledNode:
        style = dict(UA_DEFAULTS)
        if parent_style:
            for k in INHERITED:
                if k in parent_style:
                    style[k] = parent_style[k]

        if isinstance(node, ElementNode):
            matched = self._matching_rules(node)
            # sort by (specificity, order) so stable by source order
            matched.sort(key=lambda it: (it[0], it[1]))
            for _, __, decls in matched:
                style.update(decls)

            inline = node.attributes.get("style")
            if inline:
                style.update(parse_inline_style(inline))

            styled = StyledNode(node=node, style=style, children=[])
            for c in node.children:
                styled.children.append(self._style_node(c, style))
            return styled

        return StyledNode(node=node, style=style, children=[])

    def _matching_rules(self, el: ElementNode) -> List[Tuple[int, int, Dict[str, str]]]:
        out: List[Tuple[int, int, Dict[str, str]]] = []
        for r in self.rules:
            if self._selector_matches(r.selector, el):
                out.append((r.selector.specificity(), r.order, r.declarations))
        return out

    def _selector_matches(self, sel: Selector, el: ElementNode) -> bool:
        if not self._simple_matches(sel.right, el):
            return False
        if sel.left is None:
            return True
        p = el.parent
        while p is not None:
            if isinstance(p, ElementNode) and self._simple_matches(sel.left, p):
                return True
            p = p.parent
        return False

    def _simple_matches(self, s: SimpleSelector, el: ElementNode) -> bool:
        if s.tag and el.tag.lower() != s.tag:
            return False
        if s.id:
            if (el.attributes.get("id") or "").strip() != s.id:
                return False
        if s.cls:
            classes = {(el.attributes.get("class") or "").strip().split()[i]
                       for i in range(len((el.attributes.get("class") or "").strip().split()))}
            if s.cls not in classes:
                return False
        return True
