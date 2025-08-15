import skia
from draw import DrawRect, linespace, Transform, Blend, DrawRRect, paint_visual_effects, paint_outline
from layout.embed_layout import EmbedLayout, dpx
from protected_field import ProtectedField

IFRAME_WIDTH_PX = 300
IFRAME_HEIGHT_PX = 150

class IframeLayout(EmbedLayout):
    def __init__(self, node, parent, previous):
        super().__init__(node, parent, previous, None)

    def layout(self):
        super().layout()
        zoom = self.zoom.read(notify=self.width)
        width_attr = self.node.attributes.get("width")
        height_attr = self.node.attributes.get("height")
        
        if width_attr:
            self.width.set(dpx(int(width_attr) + 2, zoom))
        else:
            self.width.set(dpx(IFRAME_WIDTH_PX + 2, zoom))

        if height_attr:
            self.height.set(dpx(int(height_attr) + 2, zoom))
        else:
            self.height.set(dpx(IFRAME_HEIGHT_PX + 2, zoom))
        
        height = self.height.read(notify=self.ascent)
        self.ascent.set(-height)
        self.descent.set(0)
        
        # Set frame dimensions for child frame
        if self.node.frame and self.node.frame.loaded:
            self.node.frame.frame_height = self.height.get() - dpx(2, zoom)
            self.node.frame.frame_width = self.width.get() - dpx(2, zoom)

    def paint(self):
        cmds = []
        # Draw iframe border
        rect = skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width, self.y + self.height)
        cmds.append(DrawRect(rect, "lightgray"))
        
        # If iframe has loaded content, paint it
        if hasattr(self.node, 'frame') and self.node.frame and self.node.frame.loaded:
            # TODO: Paint iframe content
            pass
        
        return cmds

    def paint_effects(self, cmds):
        rect = self.self_rect()
        zoom = self.zoom.get()
        
        # Add border and transform for iframe content
        diff = dpx(1, zoom)
        offset = (self.x + diff, self.y + diff)
        cmds = [Transform(offset, rect, self.node, cmds)]
        inner_rect = skia.Rect.MakeLTRB(
            self.x + diff, self.y + diff,
            self.x + self.width - diff, self.y + self.height - diff)
        internal_cmds = cmds
        internal_cmds.append(Blend(1.0, "destination-in", None, [
                          DrawRRect(inner_rect, 0, "white")]))
        cmds = [Blend(1.0, "source-over", self.node, internal_cmds)]
        paint_outline(self.node, cmds, rect, zoom)
        cmds = paint_visual_effects(self.node, cmds, rect)
        return cmds
