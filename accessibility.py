from htmltree.text import Text
from htmltree.tag import Element
import skia
from draw import absolute_to_local, local_to_absolute

# Utilities duplicated to avoid circular imports

def get_tabindex(node):
    try:
        tabindex = int(node.attributes.get("tabindex", "9999999"))
    except Exception:
        tabindex = 9999999
    return 9999999 if tabindex == 0 else tabindex


def is_focusable(node):
    if not isinstance(node, Element):
        return False
    if get_tabindex(node) < 0:
        return False
    elif "tabindex" in node.attributes:
        return True
    else:
        return node.tag in ["input", "button", "a"]


class AccessibilityNode:
    def __init__(self, node):
        self.node = node
        self.children = []
        self.text = ""
        self.bounds = []
        # Determine role
        if isinstance(node, Text):
            if node.parent and is_focusable(node.parent):
                self.role = "focusable text"
            else:
                self.role = "StaticText"
        else:
            if isinstance(node, Element) and "role" in node.attributes:
                self.role = node.attributes["role"]
            elif isinstance(node, Element) and node.tag == "a":
                self.role = "link"
            elif isinstance(node, Element) and node.tag == "input":
                self.role = "textbox"
            elif isinstance(node, Element) and node.tag == "button":
                self.role = "button"
            elif isinstance(node, Element) and node.tag == "html":
                self.role = "document"
            elif isinstance(node, Element) and is_focusable(node):
                self.role = "focusable"
            else:
                self.role = "none"

    def compute_bounds(self):
        # Direct layout object
        lo = getattr(self.node, 'layout_object', None)
        if lo and hasattr(lo, 'x') and hasattr(lo, 'y') and hasattr(lo, 'width') and hasattr(lo, 'height'):
            try:
                rect = skia.Rect.MakeXYWH(lo.x, lo.y, lo.width, lo.height)
                return [rect]
            except Exception:
                pass
        # Text nodes have no bounds by themselves
        if isinstance(self.node, Text):
            return []
        # Inline container: union over its text children lines
        # Find nearest ancestor with layout_object
        inline = getattr(self.node, 'parent', None)
        while inline and not getattr(inline, 'layout_object', None):
            inline = getattr(inline, 'parent', None)
        bounds = []
        if inline and getattr(inline, 'layout_object', None):
            for line in getattr(inline.layout_object, 'children', []):
                line_bounds = skia.Rect.MakeEmpty()
                for child in getattr(line, 'children', []):
                    if getattr(child, 'node', None) and getattr(child.node, 'parent', None) == self.node:
                        try:
                            r = skia.Rect.MakeXYWH(child.x, child.y, child.width, child.height)
                            line_bounds.join(r)
                        except Exception:
                            pass
                if not line_bounds.isEmpty():
                    bounds.append(line_bounds)
        return bounds

    def build(self):
        # Recurse children (skipping none roles)
        for child_node in getattr(self.node, 'children', []):
            self.build_internal(child_node)
        # Compute text description
        if isinstance(self.node, Text):
            if self.role == "StaticText":
                self.text = repr(self.node.text)
            elif self.role == "focusable text":
                self.text = "Focusable text: " + self.node.text
        else:
            if self.role == "focusable":
                self.text = "Focusable element"
            elif self.role == "textbox":
                value = ""
                if isinstance(self.node, Element) and "value" in self.node.attributes:
                    value = self.node.attributes["value"]
                elif isinstance(self.node, Element) and self.node.tag != "input" and \
                        self.node.children and isinstance(self.node.children[0], Text):
                    value = self.node.children[0].text
                self.text = "Input box: " + value
            elif self.role == "button":
                self.text = "Button"
            elif self.role == "link":
                self.text = "Link"
            elif self.role == "alert":
                self.text = "Alert"
            elif self.role == "document":
                self.text = "Document"
        # Focus suffix
        if getattr(self.node, 'is_focused', False):
            self.text += " is focused"
        # Compute bounds after children exist
        self.bounds = self.compute_bounds()

    def build_internal(self, child_node):
        child = AccessibilityNode(child_node)
        if child.role != "none":
            self.children.append(child)
            child.build()
        else:
            for grandchild_node in getattr(child_node, 'children', []):
                self.build_internal(grandchild_node)

    def contains_point(self, x, y):
        for bound in self.bounds:
            if bound.contains(x, y):
                return True
        return False

    def hit_test(self, x, y):
        node = None
        if self.contains_point(x, y):
            node = self
        for child in self.children:
            res = child.hit_test(x, y)
            if res: node = res
        return node 
