from typing import Literal
from draw import DrawRect, DrawText
from emoji import is_emoji
from font_cache import get_font
from tag import Element
from text import Text

HSTEP, VSTEP = 13, 18
WIDTH = 800
BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]

class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []

        # Positioning
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        self.width = WIDTH - 2*HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout(1)
        self.height = child.height
        self.display_list = child.display_list

    def paint(self):
        return []

class BlockLayout:
    Indentation = 0

    def __init__(self, node, parent, previous):
        # Tree
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []

        # Layout state
        self.display_list = []
        self.line = []
        self.cursor_x = 0
        self.cursor_y = 0
        self.weight: Literal["normal", "bold"] = "normal"
        self.style: Literal["roman", "italic"] = "roman"
        self.size = 12
        self.max_width = 800

        # Positioning
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self, level):
        self.x = self.parent.x
        self.width = self.parent.width
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
            
        mode = self.layout_mode()
        if mode == "block":
            previous = None
            for child in self.node.children:
                next = BlockLayout(child, self, previous)
                self.children.append(next)
                previous = next
        else:
            self.cursor_x = 0
            self.cursor_y = 0
            self.weight = "normal"
            self.style = "roman"
            self.size = 12

            self.line = []
            self.recurse(self.node)
            self.flush()
            self.height = self.cursor_y

        for child in self.children:
            child.layout(level + 1)

        if mode == "block":
            self.height = sum([child.height for child in self.children])


    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, Element) and child.tag in BLOCK_ELEMENTS for child in self.node.children]):
            return "block"
        elif self.node.children:
            return "inline"
        else:
            return "block"

    def layout_intermediate(self):
        previous = None
        for child in self.node.children:
            next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next

    def recurse(self, tree):
        if isinstance(tree, Text):
            for word in tree.text.split():
                self.word(word)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)

    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "abbr":
            self.size -= 4
            self.weight = "bold"
            self.abbr = True
        elif tag == "pre":
            self.pre = True
        elif tag == "small":         
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.flush()
            self.cursor_y += VSTEP
        elif tag == "sup":
            self.size = int(self.size / 2)
            self.sup = True
        elif tag == "sub":
            self.size = int(self.size / 2)
            self.sub = True
        elif tag == "h1":
            self.flush()
            self.size += 4
            self.weight = "bold"
            self.text_align = "center"
            self.cursor_y += VSTEP

    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "abbr":
            self.size += 4
            self.weight = "normal"
            self.abbr = False
        elif tag == "pre":
            self.pre = False
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP
        elif tag == "sup":
            self.size *= 2
            self.sup = False
        elif tag == "sub":
            self.size *= 2
            self.sub = False
        elif tag == "h1":
            self.flush()
            self.size -= 4
            self.weight = "normal"
            self.text_align = "left"
            self.cursor_y += VSTEP

    def flush(self):
        if not self.line: return
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        max_descent = max([metric["descent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        for rel_x, word, font in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        # Move the cursor down accounting for the max descender of the current line
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = 0
        # self.cursor_y = 0
        self.line = []
    
    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
        actual_word = word.replace("\N{soft hyphen}", "")
        w = font.measure(actual_word)
        if self.cursor_x + w > self.width or word == "\n":
            self.flush()
                
        self.line.append((self.cursor_x, actual_word, font))
        self.cursor_x += w + HSTEP

    def paint(self):
        cmds = []

        if isinstance(self.node, Element) and self.node.tag == "pre":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "gray")
            cmds.append(rect)

        if self.layout_mode() == "inline":
            for x, y, word, font in self.display_list:
                cmds.append(DrawText(x, y, word, font))
        return cmds


def paint_tree(layout_object, display_list):
    display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)