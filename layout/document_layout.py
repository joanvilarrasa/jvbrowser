import skia
from layout.block_layout import HSTEP, VSTEP, WIDTH, BlockLayout
from draw import paint_visual_effects
from utils import dpx


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

    def layout(self, zoom):
        self.zoom = zoom
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        # WIDTH is device pixels; HSTEP/VSTEP are CSS pixels
        self.width = WIDTH - 2 * dpx(HSTEP, self.zoom)
        self.x = dpx(HSTEP, self.zoom)
        self.y = dpx(VSTEP, self.zoom)
        child.layout()
        self.height = child.height

    def paint(self):
        return []

    def should_paint(self):
        return False

    def self_rect(self):
        return skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width,
            self.y + self.height)

    def paint_effects(self, cmds):
        cmds = paint_visual_effects(
            self.node, cmds, self.self_rect())
        return cmds