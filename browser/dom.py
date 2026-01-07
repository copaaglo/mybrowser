from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class Node:
    parent: Optional["ElementNode"] = None


@dataclass
class TextNode(Node):
    text: str = ""


@dataclass
class ElementNode(Node):
    tag: str
    attributes: Dict[str, str] = field(default_factory=dict)
    children: List[Node] = field(default_factory=list)

    def append(self, child: Node) -> None:
        child.parent = self
        self.children.append(child)
