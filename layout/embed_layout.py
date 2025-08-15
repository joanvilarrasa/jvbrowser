import skia
from draw import DrawLine, DrawRect, DrawText, linespace, paint_visual_effects
from font_cache import get_font
from htmltree.text import Text
from protected_field import ProtectedField

def dpx(css_px, zoom):
    return css_px * zoom

def font(css_style, zoom, notify):
    weight = css_style['font-weight'].read(notify)
    style_val = css_style['font-style'].read(notify)
    try:
        size = float(css_style['font-size'].read(notify)[:-2]) * 0.75
    except:
        size = 16
    font_size = dpx(size, zoom)
    return get_font(font_size, weight, style_val)

class EmbedLayout:
    def __init__(self, node, parent, previous, frame):
        self.node = node
        self.children = []
        self.parent = parent
        self.previous = previous
        self.frame = frame
        self.has_dirty_descendants = False
        
        self.zoom = ProtectedField(self, "zoom", self.parent, [self.parent.zoom])
        self.font = ProtectedField(self, "font", self.parent,
           [self.zoom,
            self.node.style['font-weight'],
            self.node.style['font-style'],
            self.node.style['font-size']])
        self.width = ProtectedField(self, "width", self.parent, [self.zoom])
        self.height = ProtectedField(self, "height", self.parent, [self.zoom, self.font, self.width])
        self.ascent = ProtectedField(self, "ascent", self.parent, [self.height])
        self.descent = ProtectedField(self, "descent", self.parent, [])
        
        if self.previous:
            x_dependencies = [self.previous.x, self.previous.font, self.previous.width]
        else:
            x_dependencies = [self.parent.x]
        self.x = ProtectedField(self, "x", self.parent, x_dependencies)
        self.y = ProtectedField(self, "y", self.parent, [self.ascent, self.parent.y, self.parent.ascent])

    def layout(self):
        if not self.layout_needed(): return
        
        self.zoom.copy(self.parent.zoom)
        zoom = self.zoom.get()
        if self.font.dirty:
            self.font.set(font(self.node.style, zoom, notify=self.font))
        if self.previous:
            space = self.previous.font.get().measureText(" ")
            self.x.set(
                self.previous.x.get() + space + self.previous.width.get())
        else:
            self.x.copy(self.parent.x)
        self.has_dirty_descendants = False

    def layout_needed(self):
        if self.zoom.dirty: return True
        if self.width.dirty: return True
        if self.height.dirty: return True
        if self.x.dirty: return True
        if self.y.dirty: return True
        if self.font.dirty: return True
        if self.ascent.dirty: return True
        if self.descent.dirty: return True
        if self.has_dirty_descendants: return True
        return False

    def should_paint(self):
        return True

    def self_rect(self):
        return skia.Rect.MakeLTRB(
            self.x.get(), self.y.get(),
            self.x.get() + self.width.get(),
            self.y.get() + self.height.get())

    def paint_effects(self, cmds):
        cmds = paint_visual_effects(
            self.node, cmds, self.self_rect())
        return cmds
