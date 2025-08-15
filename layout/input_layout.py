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
        super().layout()
        zoom = self.zoom.read(notify=self.width)
        self.width.set(dpx(INPUT_WIDTH_PX, zoom))

        font = self.font.read(notify=self.height)
        self.height.set(linespace(font))

        height = self.height.read(notify=self.ascent)
        self.ascent.set(-height)
        self.descent.set(0) 

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

        if self.node.is_focused and self.node.tag == "input":
            cmds.append(DrawCursor(self, self.font.get().measureText(text)))

        return cmds

