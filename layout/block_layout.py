from typing import Literal
import skia
from draw import DrawRRect, paint_visual_effects, paint_outline
from font_cache import get_font
from layout.input_layout import INPUT_WIDTH_PX, InputLayout
from layout.line_layout import LineLayout
from layout.text_layout import TextLayout
from htmltree.tag import Element
from htmltree.text import Text
from utils import dpx

BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]

WIDTH = 1200
HEIGHT = 1000
HSTEP = 13
VSTEP = 18


class BlockLayout:
    Indentation = 0

    def __init__(self, node, parent, previous):
        # Tree
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        # Link layout object
        try:
            self.node.layout_object = self
        except Exception:
            pass

        # Layout state
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

    def layout(self):
        self.zoom = getattr(self.parent, 'zoom', 1)
        self.x = self.parent.x
        self.width = self.parent.width
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        if isinstance(self.node, Element) and self.node.tag == "head":
            self.height = 0
            return
            
        mode = self.layout_mode()
        if mode == "block":
            previous = None
            for child in self.node.children:
                next = BlockLayout(child, self, previous)
                self.children.append(next)
                previous = next
        else:
            self.new_line()
            self.recurse(self.node)

        for child in self.children:
            child.layout()

        self.height = sum([child.height for child in self.children])

    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, Element) and child.tag in BLOCK_ELEMENTS for child in self.node.children]):
            return "block"
        elif self.node.children or self.node.tag == "input":
            return "inline"
        else:
            return "block"

    def layout_intermediate(self):
        previous = None
        for child in self.node.children:
            next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next

    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                self.new_line()
            elif node.tag == "input" or node.tag == "button":
                self.input(node)
            else:
                for child in node.children:
                    self.recurse(child)

    def flush(self):
        if not self.line: return
        metrics = [font.getMetrics() for x, word, font, color in self.line]
        max_ascent = max([abs(metric.fAscent) for metric in metrics])
        max_descent = max([metric.fDescent for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        for rel_x, word, font, color in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.getMetrics().fAscent
            self.display_list.append((x, y, word, font, color))
        # Move the cursor down accounting for the max descender of the current line
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = 0
        # self.cursor_y = 0
        self.line = []
        
    def new_line(self):
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def paint(self):
        cmds = []
        bgcolor = self.node.style.get("background-color","transparent")
        if bgcolor != "transparent":
            radius = float(
                self.node.style.get(
                    "border-radius", "0px")[:-2])
            cmds.append(DrawRRect(
                self.self_rect(), radius, bgcolor))
        return cmds
    
    def should_paint(self):
        return isinstance(self.node, Text) or (self.node.tag != "input" and self.node.tag != "button")

    def self_rect(self):
        return skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width,
            self.y + self.height)

    # Handle text
    def word(self, node, word):
        # Get the text style from the node
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        px_size = float(node.style["font-size"][:-2])
        size = dpx(px_size * 0.75, self.zoom)
        color = node.style["color"]
        font = get_font(size, weight, style)

        w = font.measureText(word)
        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        text = TextLayout(node, word, line, previous_word)
        line.children.append(text)
        if self.cursor_x + w > self.width:
            self.new_line()
                
        # self.line.append((self.cursor_x, actual_word, font, color))
        # self.cursor_x += w + HSTEP

    # Handle input and button tags
    def input(self, node):
        w = dpx(INPUT_WIDTH_PX, self.zoom)
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        input = InputLayout(node, line, previous_word)
        line.children.append(input)

        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        px_size = float(node.style["font-size"][:-2])
        size = dpx(px_size * 0.75, self.zoom)
        font = get_font(size, weight, style)

        self.cursor_x += w + font.measureText(" ")

    def paint_effects(self, cmds):
        cmds = paint_visual_effects(
            self.node, cmds, self.self_rect())
        paint_outline(self.node, cmds, self.self_rect(), getattr(self, 'zoom', 1))
        return cmds

    def self_rect(self):
        return skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width,
            self.y + self.height)


