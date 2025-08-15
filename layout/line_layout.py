from draw import linespace, paint_visual_effects, paint_outline
import skia
from protected_field import ProtectedField

class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.has_dirty_descendants = False
        self.initialized_fields = False
        
        self.zoom = ProtectedField(self, "zoom", self.parent, [self.parent.zoom])
        self.width = ProtectedField(self, "width", self.parent, [self.parent.width])
        self.x = ProtectedField(self, "x", self.parent, [self.parent.x])
        
        if self.previous:
            y_dependencies = [self.previous.y, self.previous.height]
        else:
            y_dependencies = [self.parent.y]
        self.y = ProtectedField(self, "y", self.parent, y_dependencies)
        
        self.height = ProtectedField(self, "height", self.parent)
        self.ascent = ProtectedField(self, "ascent", self.parent)
        self.descent = ProtectedField(self, "descent", self.parent)

    def layout(self):
        if not self.layout_needed(): return
        
        self.width.copy(self.parent.width)
        self.x.copy(self.parent.x)
        self.zoom.copy(self.parent.zoom)
        if self.previous:
            prev_y = self.previous.y.read(notify=self.y)
            prev_height = self.previous.height.read(notify=self.y)
            self.y.set(prev_y + prev_height)
        else:
            self.y.copy(self.parent.y)

        # Layout the words in the line so that we have information about their font, width, and height
        for word in self.children:
            word.layout()
        
        if not self.initialized_fields:
            self.ascent.set_dependencies([child.ascent for child in self.children])
            self.descent.set_dependencies([child.descent for child in self.children])
            self.initialized_fields = True
        
        if not self.children:
            self.height.set(0)
            return

        self.ascent.set(max([
            -child.ascent.read(notify=self.ascent)
            for child in self.children
        ]))

        self.descent.set(max([
            child.descent.read(notify=self.descent)
            for child in self.children
        ]))

        for child in self.children:
            new_y = self.y.read(notify=child.y)
            new_y += self.ascent.read(notify=child.y)
            new_y += child.ascent.read(notify=child.y)
            child.y.set(new_y)

        max_ascent = self.ascent.read(notify=self.height)
        max_descent = self.descent.read(notify=self.height)
        self.height.set(max_ascent + max_descent)
        self.has_dirty_descendants = False

    def layout_needed(self):
        if self.zoom.dirty: return True
        if self.width.dirty: return True
        if self.height.dirty: return True
        if self.x.dirty: return True
        if self.y.dirty: return True
        if self.ascent.dirty: return True
        if self.descent.dirty: return True
        if self.has_dirty_descendants: return True
        return False

    def paint(self):
        return []

    def should_paint(self):
        return False

    def self_rect(self):
        return skia.Rect.MakeLTRB(
            self.x.get(), self.y.get(),
            self.x.get() + self.width.get(),
            self.y.get() + self.height.get())

    def paint_effects(self, cmds):
        cmds = paint_visual_effects(
            self.node, cmds, self.self_rect())
        outline_rect = skia.Rect.MakeEmpty()
        outline_node = None
        for child in self.children:
            parent_node = getattr(child.node, 'parent', None)
            if parent_node and getattr(parent_node, 'is_focused', False):
                outline_rect.join(child.self_rect())
                outline_node = parent_node
        if outline_node:
            paint_outline(outline_node, cmds, outline_rect, getattr(self, 'zoom', 1))
        return cmds