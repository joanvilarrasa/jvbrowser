from typing import Literal
import skia
<<<<<<< HEAD
from draw import DrawRRect, paint_visual_effects, paint_outline
=======
from draw import DrawRRect, paint_visual_effects, DrawCursor
>>>>>>> 3e07826 (Done with the project, pretty good book)
from font_cache import get_font
from layout.input_layout import INPUT_WIDTH_PX, InputLayout
from layout.image_layout import ImageLayout
from layout.iframe_layout import IframeLayout, IFRAME_WIDTH_PX
from layout.embed_layout import dpx
from layout.line_layout import LineLayout
from layout.text_layout import TextLayout
from htmltree.tag import Element
from htmltree.text import Text
<<<<<<< HEAD
from utils import dpx
=======
from utils import tree_to_list
from protected_field import ProtectedField
>>>>>>> 3e07826 (Done with the project, pretty good book)

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
<<<<<<< HEAD
        self.children = []
        # Link layout object
        try:
            self.node.layout_object = self
        except Exception:
            pass

=======
        self.has_dirty_descendants = False
        
>>>>>>> 3e07826 (Done with the project, pretty good book)
        # Layout state
        self.line = []
        self.cursor_x = 0
        self.cursor_y = 0
        self.weight: Literal["normal", "bold"] = "normal"
        self.style: Literal["roman", "italic"] = "roman"
        self.size = 12
        self.max_width = 800

        # Protected fields
        self.children = ProtectedField(self, "children", self.parent)
        self.zoom = ProtectedField(self, "zoom", self.parent, [self.parent.zoom])
        self.width = ProtectedField(self, "width", self.parent, [self.parent.width])
        self.x = ProtectedField(self, "x", self.parent, [self.parent.x])
        
        if self.previous:
            y_dependencies = [self.previous.y, self.previous.height]
        else:
            y_dependencies = [self.parent.y]
        self.y = ProtectedField(self, "y", self.parent, y_dependencies)
        
        self.height = ProtectedField(self, "height", self.parent)

    def layout(self):
        if not self.layout_needed(): return
        
        self.x.copy(self.parent.x)
        self.width.copy(self.parent.width)
        self.zoom.copy(self.parent.zoom)
        if self.previous:
            prev_y = self.previous.y.read(notify=self.y)
            prev_height = self.previous.height.read(notify=self.y)
            self.y.set(prev_y + prev_height)
        else:
            self.y.copy(self.parent.y)

        if isinstance(self.node, Element) and self.node.tag == "head":
            self.height.set(0)
            return
            
        mode = self.layout_mode()
        if mode == "block":
            if self.children.dirty:
                children = []
                previous = None
                for child in self.node.children:
                    next = BlockLayout(child, self, previous)
                    children.append(next)
                    previous = next
                self.children.set(children)
                
                height_dependencies = [child.height for child in children]
                height_dependencies.append(self.children)
                self.height.set_dependencies(height_dependencies)
        else:
            if self.children.dirty:
                self.temp_children = []
                self.new_line()
                self.recurse(self.node)
                self.children.set(self.temp_children)
                self.temp_children = None
                
                height_dependencies = [child.height for child in self.temp_children]
                height_dependencies.append(self.children)
                self.height.set_dependencies(height_dependencies)

        assert not self.children.dirty
        for child in self.children.get():
            child.layout()

        assert not self.children.dirty
        children = self.children.read(notify=self.height)
        new_height = sum([
            child.height.read(notify=self.height)
            for child in children
        ])
        self.height.set(new_height)
        self.has_dirty_descendants = False

    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, Element) and child.tag in BLOCK_ELEMENTS for child in self.node.children]):
            return "block"
        elif self.node.children or self.node.tag in ["input", "img", "iframe"]:
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
            elif node.tag == "img":
                self.image(node)
            elif node.tag == "iframe":
                self.iframe(node)
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
        last_line = self.temp_children[-1] if self.temp_children else None
        new_line = LineLayout(self.node, self, last_line)
        self.temp_children.append(new_line)

    def layout_needed(self):
        if self.zoom.dirty: return True
        if self.width.dirty: return True
        if self.height.dirty: return True
        if self.x.dirty: return True
        if self.y.dirty: return True
        if self.children.dirty: return True
        if self.has_dirty_descendants: return True
        return False

    def paint(self):
        assert not self.children.dirty
        cmds = []
        bgcolor = self.node.style["background-color"].get()
        if bgcolor != "transparent":
            radius = float(
                self.node.style["border-radius"].get()[:-2])
            cmds.append(DrawRRect(
                self.self_rect(), radius, bgcolor))
        
        if self.node.is_focused and "contenteditable" in self.node.attributes:
            text_nodes = [
                t for t in tree_to_list(self, [])
                if isinstance(t, TextLayout)
            ]
            if text_nodes:
                cmds.append(DrawCursor(text_nodes[-1], text_nodes[-1].width.get()))
            else:
                cmds.append(DrawCursor(self, 0))
        
        return cmds
    
    def should_paint(self):
        return isinstance(self.node, Text) or (self.node.tag not in ["input", "button", "img", "iframe"])

    def self_rect(self):
        return skia.Rect.MakeLTRB(
            self.x.get(), self.y.get(),
            self.x.get() + self.width.get(),
            self.y.get() + self.height.get())

    # Handle text
    def word(self, node, word):
<<<<<<< HEAD
        # Get the text style from the node
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        px_size = float(node.style["font-size"][:-2])
        size = dpx(px_size * 0.75, self.zoom)
        color = node.style["color"]
        font = get_font(size, weight, style)
=======
        zoom = self.zoom.read(notify=self.children)
        node_font = font(node.style, zoom, notify=self.children)
>>>>>>> 3e07826 (Done with the project, pretty good book)

        w = node_font.measureText(word)
        line = self.temp_children[-1]
        previous_word = line.children[-1] if line.children else None
        text = TextLayout(node, word, line, previous_word)
        line.children.append(text)
        width = self.width.read(notify=self.children)
        if self.cursor_x + w > width:
            self.new_line()
                
        # self.line.append((self.cursor_x, actual_word, font, color))
        # self.cursor_x += w + HSTEP

    # Handle input and button tags
    def input(self, node):
<<<<<<< HEAD
        w = dpx(INPUT_WIDTH_PX, self.zoom)
        if self.cursor_x + w > self.width:
=======
        zoom = self.zoom.read(notify=self.children)
        w = dpx(INPUT_WIDTH_PX, zoom)
        width = self.width.read(notify=self.children)
        if self.cursor_x + w > width:
>>>>>>> 3e07826 (Done with the project, pretty good book)
            self.new_line()
        line = self.temp_children[-1]
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

    def image(self, node):
        zoom = self.zoom.read(notify=self.children)
        if "width" in node.attributes:
            w = dpx(int(node.attributes["width"]), zoom)
        else:
            w = dpx(node.image.width(), zoom)
        width = self.width.read(notify=self.children)
        if self.cursor_x + w > width:
            self.new_line()
        line = self.temp_children[-1]
        previous_word = line.children[-1] if line.children else None
        image = ImageLayout(node, line, previous_word)
        line.children.append(image)

        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style)

        self.cursor_x += w + font.measureText(" ")

    def iframe(self, node):
        zoom = self.zoom.read(notify=self.children)
        if "width" in node.attributes:
            w = dpx(int(node.attributes["width"]), zoom)
        else:
            w = dpx(IFRAME_WIDTH_PX + 2, zoom)
        width = self.width.read(notify=self.children)
        if self.cursor_x + w > width:
            self.new_line()
        line = self.temp_children[-1]
        previous_word = line.children[-1] if line.children else None
        iframe = IframeLayout(node, line, previous_word)
        line.children.append(iframe)

        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
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


