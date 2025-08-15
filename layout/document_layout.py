import skia
from layout.block_layout import HSTEP, VSTEP, WIDTH, BlockLayout
from draw import paint_visual_effects
<<<<<<< HEAD
from utils import dpx
=======
from protected_field import ProtectedField
>>>>>>> 3e07826 (Done with the project, pretty good book)


class DocumentLayout:
    def __init__(self, node, frame):
        self.node = node
        self.parent = None
        self.children = []
        self.frame = frame
        self.has_dirty_descendants = False
        self.zoom = ProtectedField(self, "zoom", None, [])
        self.width = ProtectedField(self, "width", None, [])
        self.x = ProtectedField(self, "x", None, [])
        self.y = ProtectedField(self, "y", None, [])
        self.height = ProtectedField(self, "height")

        # Positioning
        self.x_pos = None
        self.y_pos = None
        self.width_val = None
        self.height_val = None

<<<<<<< HEAD
    def layout(self, zoom):
        self.zoom = zoom
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        # WIDTH is device pixels; HSTEP/VSTEP are CSS pixels
        self.width = WIDTH - 2 * dpx(HSTEP, self.zoom)
        self.x = dpx(HSTEP, self.zoom)
        self.y = dpx(VSTEP, self.zoom)
=======
    def layout(self, width, zoom):
        if not self.layout_needed(): return
        
        if not self.children:
            child = BlockLayout(self.node, self, None)
            self.children = [child]
            self.height.set_dependencies([child.height])
        else:
            child = self.children[0]
        self.width.set(width - 2 * dpx(HSTEP, zoom))
        self.x.set(dpx(HSTEP, zoom))
        self.y.set(dpx(VSTEP, zoom))
        self.zoom.set(zoom)
        child.zoom.mark()
>>>>>>> 3e07826 (Done with the project, pretty good book)
        child.layout()
        self.height.copy(child.height)
        self.has_dirty_descendants = False

    def paint(self):
        return []

    def should_paint(self):
        return False

    def self_rect(self):
        return skia.Rect.MakeLTRB(
            self.x.get(), self.y.get(),
            self.x.get() + self.width.get(),
            self.y.get() + self.height.get())

    def layout_needed(self):
        if self.zoom.dirty: return True
        if self.width.dirty: return True
        if self.height.dirty: return True
        if self.x.dirty: return True
        if self.y.dirty: return True
        if self.has_dirty_descendants: return True
        return False

    def paint_effects(self, cmds):
        cmds = paint_visual_effects(
            self.node, cmds, self.self_rect())
        return cmds