import skia
from draw import DrawLine, DrawRect, DrawText, linespace, DrawCursor
from font_cache import get_font
from htmltree.text import Text
<<<<<<< HEAD
from draw import paint_visual_effects, paint_outline
from utils import dpx
=======
from draw import paint_visual_effects
from layout.embed_layout import EmbedLayout, dpx
from protected_field import ProtectedField
>>>>>>> 3e07826 (Done with the project, pretty good book)

INPUT_WIDTH_PX = 200

class InputLayout(EmbedLayout):
    def __init__(self, node, parent, previous):
        super().__init__(node, parent, previous, None)

    def layout(self):
<<<<<<< HEAD
        self.zoom = getattr(self.parent, 'zoom', 1)
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        px_size = float(self.node.style["font-size"][:-2])
        size = dpx(px_size * 0.75, getattr(self.parent, 'zoom', 1))
        self.font = get_font(size, weight, style)
        self.width = dpx(INPUT_WIDTH_PX, getattr(self.parent, 'zoom', 1))
        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x
        self.height = linespace(self.font) 
=======
        super().layout()
        zoom = self.zoom.read(notify=self.width)
        self.width.set(dpx(INPUT_WIDTH_PX, zoom))

        font = self.font.read(notify=self.height)
        self.height.set(linespace(font))

        height = self.height.read(notify=self.ascent)
        self.ascent.set(-height)
        self.descent.set(0) 
>>>>>>> 3e07826 (Done with the project, pretty good book)

    def paint(self):
        cmds = []
        bgcolor = self.node.style.get("background-color","transparent")
        if bgcolor != "transparent":
            rect = DrawRect(skia.Rect.MakeLTRB(self.x, self.y, self.x + self.width, self.y + self.height), bgcolor)
            cmds.append(rect)

        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
        elif self.node.tag == "button":
            if len(self.node.children) == 1 and isinstance(self.node.children[0], Text):
                text = self.node.children[0].text
            else:
                print("Ignoring HTML contents inside button")
                text = ""
        color = self.node.style["color"].get()
        cmds.append(DrawText(self.x.get(), self.y.get(), text, self.font.get(), color))

<<<<<<< HEAD
        if getattr(self.node, 'is_focused', False) and self.node.tag == "input":
            cx = self.x + self.font.measureText(text)
            cmds.append(DrawLine(
                cx, self.y, cx, self.y + self.height, "black", 1))

        return cmds

    def should_paint(self):
        return True

    def self_rect(self):
        return skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width,
            self.y + self.height)

    def paint_effects(self, cmds):
        cmds = paint_visual_effects(
            self.node, cmds, self.self_rect())
        paint_outline(self.node, cmds, self.self_rect(), getattr(self, 'zoom', 1))
        return cmds
=======
        if self.node.is_focused and self.node.tag == "input":
            cmds.append(DrawCursor(self, self.font.get().measureText(text)))

        return cmds

>>>>>>> 3e07826 (Done with the project, pretty good book)
