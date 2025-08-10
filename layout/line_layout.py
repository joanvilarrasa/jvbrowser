from draw import linespace, paint_visual_effects, paint_outline
import skia

class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        try:
            self.node.layout_object = self
        except Exception:
            pass

    def layout(self):
        self.zoom = getattr(self.parent, 'zoom', 1)
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        # Layout the words in the line so that we have information about their font, width, and height
        for word in self.children:
            word.layout()
        max_ascent = min([word.font.getMetrics().fAscent for word in self.children])
        baseline = self.y + 1.25 * max_ascent

        # Set the y position of each word depending on the other words in the same line
        for word in self.children:
            word.y = baseline - word.font.getMetrics().fAscent

        max_descent = max([word.font.getMetrics().fDescent for word in self.children])

        self.height = max_descent - max_ascent

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